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
| Modules per formation | 6 |
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
| `etudiants` | ~13,000 students with `formation_id` and `groupe` assignments |
| `professeurs` | 540 professors linked to departments |
| `lieu_examens` | 130 exam rooms (Amphitheatres + Salles TD) |
| `examens` | Scheduled exams with `formation_id` and `groupes` for room assignment |
| `surveillances` | Proctor assignments (exam + professor) |

**Note:** There is no `inscriptions` table. Students are implicitly enrolled in all modules of their formation.

## The Core Challenge: Graph Coloring

The student constraint creates a **graph coloring problem**:

- Each module is a node in a conflict graph
- Two modules are connected if they share at least one student
- Modules with conflicts cannot be scheduled on the same day
- The **chromatic number** = minimum days needed for zero violations

### Simplified Enrollment Model

After re-thinking the enrollment system, we adopted a **formation-based implicit enrollment** model:

- Students are automatically enrolled in **all 6 modules of their current formation**
- **No retakes** - students only take current semester modules
- Enrollment is derived from `etudiants.formation_id` → `modules.formation_id`

This simplification has major benefits:

| Aspect | Old System (inscriptions) | New System (formation-based) |
|--------|---------------------------|------------------------------|
| Enrollment tracking | Explicit `inscriptions` table | Implicit via `formation_id` |
| Modules per student | 10+ (with retakes) | 6 (current formation only) |
| Chromatic number | Up to 18 | 6 (formation modules share students) |
| Data complexity | 131,902 enrollment records | No extra table needed |
| Conflict density | High (cross-semester conflicts) | Low (only within-formation conflicts) |

### Why This Works

Students within the same formation share all 6 modules, creating a **clique** (complete subgraph) of size 6. However, students in different formations have **zero conflicts** since they share no modules.

This means:
- **Chromatic number = 6** (only 6 modules per student need different days)
- **18 exam days** provides 3x headroom for load balancing
- Conflict graph is highly structured (disjoint cliques)

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

### Phase 3: Room Assignment (Group-Based)

Room assignment now considers **student groups within formations** for better organization:

For each time slot:
1. Get all groups enrolled in each module (via `student_info`)
2. Sort groups by size (largest first)
3. Assign rooms based on group size:
   - **Large groups (>20 students)**: Assign to Amphitheatre (60 capacity)
   - **Small groups (≤20 students)**: Assign to Salle TD (20 capacity)
4. **Combine groups from same formation** when they fit in one room
5. Track `formation_id` and `groupes` (comma-separated) in exam records

Room assignment priorities:
- Prefer Amphitheatres for large groups
- Combine small groups from same formation to reduce room count
- Fallback to multiple Salles TD if no Amphitheatre available

### Phase 4: Professor Assignment

Proctors needed vary by room type:
- **Salle TD (20 seats)**: 1 proctor
- **Amphitheatre (60 seats)**: 3 proctors (1 per 20 students)

For each exam:
1. Calculate total proctors needed based on assigned rooms
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
| **Execution time** | <1 second |
| **Students** | ~13,000 |
| **Modules scheduled** | ~1,116 |
| **Exam entries** | Variable (depends on group distribution) |
| **Exam days** | 18 (no Fridays, 3 weeks) |
| **Slots per day** | 4 (08:00, 10:30, 13:00, 15:30) |
| **Student violations** | 0 |
| **Professor violations** | 0 |
| **Chromatic number** | 6 (formation-based enrollment) |

### Constraint Verification

| Constraint | Status |
|------------|--------|
| Max 1 exam/day per student | **PASS** (0 violations) |
| Max 3 exams/day per professor | **PASS** (0 violations) |
| Room capacity | **PASS** (group-based assignment) |
| Department priority | **PASS** (same-dept professors first) |
| Equal proctoring sessions | **PASS** (balanced distribution) |
| No Fridays | **PASS** (excluded from schedule) |
| Under 45 seconds | **PASS** (<1 second) |

## Resource Utilization

### Room Capacity
- Total capacity per slot: 3,400 seats (20 Amphis × 60 + 110 Salles × 20)
- Group-based assignment ensures efficient room usage
- Current resources are sufficient

### Professor Workload
- 540 professors across 7 departments
- Proctoring sessions distributed based on room assignments
- Amphitheatres require 3 proctors each, Salles TD require 1
- Max 3 exams per day per professor (constraint satisfied)

## Running the Optimizer

```bash
source .venv/bin/activate
python -m scripts.optimize
```

Since enrollment is now implicit (formation-based), there's no need to regenerate enrollment data separately. To repopulate the entire database:

```bash
python -m scripts.populate_db
```

## Key Learnings

### 1. Simpler Enrollment = Lower Chromatic Number

The old inscription-based system with retakes created a chromatic number of 18 (exactly matching available days). By switching to formation-based implicit enrollment:
- Chromatic number dropped to 6
- 18 exam days provides 3x headroom
- Zero risk of student violations

### 2. Implicit Enrollment Eliminates Complexity

Removing the explicit `inscriptions` table simplified:
- Database schema (one fewer table)
- Data population (no enrollment generation logic)
- Conflict calculation (direct formation_id join)
- Maintenance (no inscription-module consistency issues)

### 3. Group-Based Room Assignment Improves Organization

Tracking `formation_id` and `groupes` in exam records enables:
- Students to know which room to go to based on their group
- Better room utilization by combining small groups
- Cleaner PDF schedule generation per formation

### 4. Greedy Algorithms Suffice

Despite graph coloring being NP-hard, greedy heuristics with good ordering find valid solutions quickly for this problem size.

### 5. Current Resources are Adequate

The flexible resources (130 rooms, 540 professors) are sufficient without modification.

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

1. **Professor availability**: Support for unavailable days/slots
2. **Exam duration**: Variable-length exams
3. **Department clustering**: Group department exams on consecutive days
4. **Manual overrides**: Allow fixing certain exams before optimization
5. **Retake support**: Optional inscription-based enrollment for students retaking modules
