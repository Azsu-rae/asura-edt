# Exam Schedule Optimization

This document describes the optimization process for generating university exam schedules that satisfy multiple constraints.

## Problem Context

A faculty with 13,000+ students across 7 departments needs to schedule exams for all modules while respecting various constraints. Manual scheduling is error-prone and time-consuming, so we implemented an automated optimization algorithm.

## Requirements

### Fixed Resources (from backend_requirements.txt)

| Resource | Value |
|----------|-------|
| Students | 13,000 |
| Departments | 7 |
| Formations | ~200 |
| Modules per formation | 6-9 |
| Salle TD capacity | 20 seats |
| Amphi capacity | 60 seats |
| Exam period | 3 weeks (18 days, no Fridays) |
| Sessions per day | 4 |

### Flexible Resources (can be adjusted)

| Resource | Current Value |
|----------|---------------|
| Amphitheaters | 20 (1,200 seats total) |
| Salles TD | 110 (2,200 seats total) |
| Professors | 540 (62-105 per department) |

### Optimization Constraints

1. **Student constraint**: Maximum 1 exam per day per student
2. **Professor constraint**: Maximum 3 exams per day per professor
3. **Room capacity**: Total assigned room capacity must accommodate all enrolled students
4. **Department priority**: Professors proctor exams in their own department first
5. **Equal workload**: All professors have approximately equal proctoring sessions
6. **Time limit**: Optimization must complete in under 45 seconds

## Database Schema

| Table | Description |
|-------|-------------|
| `departements` | 7 departments (Physique, Chimie, Mathematique, Informatique, Agronomie, Biologie, Geologie) |
| `specialites` | Programs within departments (Licence/Master cycles) |
| `formations` | Specific semester instances (e.g., "Informatique Licence S3") |
| `modules` | 6 modules per formation, 1,116 total |
| `etudiants` | 12,901 students |
| `inscriptions` | Student-module enrollments (131,902 records) |
| `professeurs` | 540 professors linked to departments |
| `lieu_examens` | 130 exam rooms |
| `examens` | Scheduled exams (module + room + datetime) |
| `surveillances` | Proctor assignments (exam + professor) |

## The Core Challenge: Graph Coloring

The student constraint creates a **graph coloring problem**:

- Each module is a node in a conflict graph
- Two modules are connected if they share at least one student
- Modules with conflicts cannot be scheduled on the same day
- The **chromatic number** = minimum days needed for zero violations

### The Enrollment Challenge

To achieve 130,000 enrollments with 13,000 students requires ~10 modules per student on average. This is achieved through:

- **6 current formation modules** (mandatory)
- **4+ retake modules** from previous semesters

However, retake patterns directly affect the chromatic number:

| Enrollment Model | Enrollments | Chromatic Number | Feasible in 18 days? |
|------------------|-------------|------------------|---------------------|
| Formation only (6 modules) | 77,406 | 6 | Yes |
| +1 previous semester | 91,640 | 12 | Yes |
| +2 previous semesters | 131,902 | 18 | Yes (exact fit) |
| +All previous semesters | 131,992 | 36 | No (violations) |
| +Cross-department | 129,391 | 113 | No (severe violations) |

### Solution: Controlled Retake Pattern

The key insight: **limiting retakes to 2 previous semesters of the same specialty** achieves 130k+ enrollments while keeping chromatic number at exactly 18 (matching available days).

```python
# Retakes from up to 2 PREVIOUS semesters of the SAME specialty
previous_formations = [
    f_id for f_id, sem in formations_by_specialty.get(specialite_id, [])
    if current_semester - 2 <= sem < current_semester
]
```

## Algorithm

The optimization runs in 6 phases, completing in under 1 second:

### Phase 1: Build Conflict Graph

```
For each student:
    For each pair of modules they're enrolled in:
        Mark those modules as conflicting
```

Time complexity: O(S × M²) where S = students, M = avg modules per student

### Phase 2: Slot Assignment (Graph Coloring)

Uses a **greedy coloring** algorithm with the **largest-degree-first** heuristic:

1. Calculate chromatic number (minimum days needed)
2. Sort modules by number of conflicts (descending)
3. For each module:
   - Find days without conflicts
   - Choose the day+slot with lowest load (for balance)
   - If no conflict-free day exists, choose day with minimum conflicts

### Phase 3: Room Assignment

For each time slot:
1. Sort modules by enrollment size (descending)
2. Greedily assign rooms until capacity is met
3. Large exams span multiple rooms

### Phase 4: Professor Assignment

For each exam:
1. Calculate proctors needed (1 per room)
2. First, assign eligible same-department professors (sorted by current load)
3. If needed, assign professors from other departments
4. Eligibility: <3 exams that day AND below session quota

### Phase 5: Balance Verification

Check distribution of proctoring sessions. Target: range ≤ 1.

### Phase 6: Database Write

Insert exam and surveillance records with proper datetime formatting.
Time slots: 08:00, 10:30, 13:00, 15:30

## Final Results

| Metric | Value |
|--------|-------|
| **Execution time** | 0.95 seconds |
| **Enrollments** | 131,902 |
| **Modules scheduled** | 1,116 |
| **Exam entries** | 4,619 (includes multi-room splits) |
| **Exam days** | 18 (no Fridays) |
| **Slots per day** | 4 |
| **Student violations** | 0 |
| **Professor violations** | 0 |
| **Same-department proctors** | 87.7% |
| **Session range** | 1 (8-9 per professor) |

### Constraint Verification

| Constraint | Status |
|------------|--------|
| Max 1 exam/day per student | **PASS** (0 violations) |
| Max 3 exams/day per professor | **PASS** (0 violations) |
| Room capacity | **PASS** (0 violations) |
| Department priority | **PASS** (87.7% same-dept) |
| Equal proctoring sessions | **PASS** (range=1) |
| No Fridays | **PASS** (0 exams) |
| Under 45 seconds | **PASS** (0.95s) |

## Resource Utilization

### Room Capacity
- Total capacity per slot: 3,400 seats
- Peak usage: All 130 rooms used in busiest slots
- Current resources are sufficient

### Professor Workload
- 540 professors
- 4,619 proctoring sessions total
- 8-9 sessions per professor (balanced)
- Max 3 exams per day per professor (constraint satisfied)

## Running the Optimizer

```bash
source .venv/bin/activate
python -m scripts.optimize
```

To regenerate enrollment data:
```bash
python -c "
from scripts.helpers import create_connection
from scripts.populate_db import insert_inscriptions
conn = create_connection()
cur = conn.cursor()
cur.execute('DELETE FROM inscriptions')
conn.commit()
insert_inscriptions(conn, cur)
conn.close()
"
```

## Key Learnings

### 1. Chromatic Number is the Critical Constraint

With fixed exam days (18), the chromatic number of the conflict graph determines feasibility. Enrollment patterns that create chromatic numbers > 18 result in unavoidable student violations.

### 2. Retake Patterns Control Feasibility

Cross-specialty or cross-department retakes create dense conflict graphs. Limiting retakes to recent semesters of the same specialty keeps conflicts manageable while achieving enrollment targets.

### 3. Exact Fit is Possible

With careful tuning, we achieved chromatic number = 18 (exactly matching available days) while hitting 130k+ enrollments. This required:
- 10-14 modules per student target
- Retakes from 2 previous semesters only
- Same specialty restriction

### 4. Greedy Algorithms Suffice

Despite graph coloring being NP-hard, greedy heuristics with good ordering find valid solutions quickly for this problem size.

### 5. Current Resources are Adequate

The flexible resources (130 rooms, 540 professors) are sufficient for 130k enrollments without modification.

## Frontend Application

A Streamlit web interface provides access to all scheduling features.

### Running the Frontend

```bash
./run_frontend.sh
# or
source .venv/bin/activate && streamlit run frontend/app.py
```

Access at: http://localhost:8501

### Pages

| Page | Description |
|------|-------------|
| **Dashboard** | KPIs, statistics, performance benchmarks |
| **Emplois du Temps** | View/export schedules by formation (PDF) |
| **Professeurs** | Professor surveillance schedules |
| **Salles** | Room occupancy analysis |
| **Conflits** | Conflict detection and validation |
| **Optimisation** | Run optimizer and verify constraints |

### Features

- **PDF Export**: Generate schedules per formation with all groups
- **Filtering**: By department, specialty, formation
- **KPIs**: Professor hours, room utilization rates
- **Benchmarks**: Query execution times
- **Conflict Detection**: Student/professor/room conflicts by department
- **Bulk Export**: ZIP file with all formation PDFs

## Future Improvements

1. **Room type preferences**: Assign large exams to amphitheaters first
2. **Professor availability**: Support for unavailable days/slots
3. **Exam duration**: Variable-length exams
4. **Department clustering**: Group department exams on consecutive days
5. **Manual overrides**: Allow fixing certain exams before optimization
