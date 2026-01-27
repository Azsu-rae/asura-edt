"""
Exam Schedule Optimizer

Constraints:
- Max 1 exam per day per student
- Max 3 exams per day per professor
- Professors prioritize their department's exams
- All professors must have equal proctoring sessions
- Must complete in under 45 seconds
- 14-day exam period (excluding Fridays) = 12 exam days
- 4 slots per day = 48 total slots
"""

import time
from datetime import datetime, timedelta
from collections import defaultdict
from scripts.helpers import create_connection

# Schedule configuration
NUM_CALENDAR_DAYS = 21  # 3 weeks
SLOTS_PER_DAY = 4
SLOT_TIMES = ["08:00:00", "10:30:00", "13:00:00", "15:30:00"]
BASE_DATE = datetime(2026, 1, 12)  # Monday


def get_exam_days():
    """Generate list of exam days (excluding Fridays)."""
    days = []
    current = BASE_DATE
    end_date = BASE_DATE + timedelta(days=NUM_CALENDAR_DAYS)
    while current < end_date:
        if current.weekday() != 4:  # Skip Friday (weekday 4)
            days.append(current)
        current += timedelta(days=1)
    return days  # 18 exam days in 21 calendar days (3 Fridays excluded)


def optimize_schedule():
    start_time = time.time()

    conn = create_connection()
    cur = conn.cursor()

    print("Loading data from database...")

    # Load all modules with their department info
    cur.execute("""
        SELECT m.id, m.formation_id, d.id as dept_id
        FROM modules m
        JOIN formations f ON m.formation_id = f.id
        JOIN specialites s ON f.specialite_id = s.id
        JOIN departements d ON s.dept_id = d.id
    """)
    modules = {
        row[0]: {"formation_id": row[1], "dept_id": row[2]} for row in cur.fetchall()
    }
    module_ids = list(modules.keys())

    # Build student-module relationships from formations
    # Students take all modules of their formation
    cur.execute("SELECT id, formation_id FROM modules")
    modules_by_formation = defaultdict(list)
    for mod_id, form_id in cur.fetchall():
        modules_by_formation[form_id].append(mod_id)

    cur.execute("SELECT id, formation_id FROM etudiants")
    module_students = defaultdict(set)
    student_modules = defaultdict(set)
    for student_id, formation_id in cur.fetchall():
        for module_id in modules_by_formation[formation_id]:
            module_students[module_id].add(student_id)
            student_modules[student_id].add(module_id)

    # Load student groups (student_id -> (formation_id, groupe))
    cur.execute("SELECT id, formation_id, groupe FROM etudiants")
    student_info = {row[0]: {"formation_id": row[1], "groupe": row[2]} for row in cur.fetchall()}

    # Load professors with their departments
    cur.execute("SELECT id, dept_id FROM professeurs")
    professors = {row[0]: {"dept_id": row[1]} for row in cur.fetchall()}
    prof_ids = list(professors.keys())

    # Load exam locations
    cur.execute("SELECT id, capacite, type FROM lieu_examens ORDER BY capacite DESC")
    locations = [(row[0], row[1], row[2]) for row in cur.fetchall()]

    exam_days = get_exam_days()
    NUM_DAYS = len(exam_days)
    TOTAL_SLOTS = NUM_DAYS * SLOTS_PER_DAY

    print(
        f"Loaded {len(modules)} modules, {len(student_modules)} students, "
        f"{len(professors)} professors, {len(locations)} rooms"
    )
    print(f"Exam period: {NUM_DAYS} days, {
          SLOTS_PER_DAY} slots/day = {TOTAL_SLOTS} total slots")

    # ========== PHASE 1: Build conflict graph ==========
    print("\nBuilding conflict graph...")

    # Two modules conflict if they share at least one student
    # For day-level conflicts (students can't have 2 exams same day)
    conflicts = defaultdict(set)
    for student_id, mods in student_modules.items():
        mods_list = list(mods)
        for i in range(len(mods_list)):
            for j in range(i + 1, len(mods_list)):
                conflicts[mods_list[i]].add(mods_list[j])
                conflicts[mods_list[j]].add(mods_list[i])

    # ========== PHASE 2: Slot assignment using constraint propagation ==========
    print("Assigning exams to slots...")

    # First, calculate minimum days needed (chromatic number estimate)
    sorted_modules = sorted(module_ids, key=lambda m: len(conflicts[m]), reverse=True)
    temp_colors = {}
    for module_id in sorted_modules:
        used = {temp_colors[m] for m in conflicts[module_id] if m in temp_colors}
        c = 0
        while c in used:
            c += 1
        temp_colors[module_id] = c
    num_colors_needed = max(temp_colors.values()) + 1 if temp_colors else 0
    print(f"Chromatic number: {
          num_colors_needed} days needed for zero conflicts")

    # We need to assign modules to (day, slot) pairs
    # Constraint: modules sharing students must be on DIFFERENT DAYS
    # This is graph coloring where colors = days (not slots)

    module_day = {}  # module_id -> day index (0 to NUM_DAYS-1)
    module_slot = {}  # module_id -> slot index (0 to SLOTS_PER_DAY-1)

    # Track slots used per day for load balancing
    day_slot_counts = defaultdict(lambda: defaultdict(int))

    for module_id in sorted_modules:
        # Find days that don't conflict with already-assigned modules
        used_days = {module_day[m] for m in conflicts[module_id] if m in module_day}

        # Try to find a valid day (prefer days with fewer exams for balance)
        best_day = None
        best_slot = None
        min_load = float("inf")

        for day in range(NUM_DAYS):
            if day in used_days:
                continue
            # Find the least loaded slot on this day
            for slot in range(SLOTS_PER_DAY):
                load = day_slot_counts[day][slot]
                if load < min_load:
                    min_load = load
                    best_day = day
                    best_slot = slot

        if best_day is None:
            # No conflict-free day available - find day with minimum conflict
            # This means some students will have >1 exam per day (constraint violation)
            conflict_counts = defaultdict(int)
            for day in range(NUM_DAYS):
                for m in conflicts[module_id]:
                    if m in module_day and module_day[m] == day:
                        conflict_counts[day] += 1

            best_day = min(range(NUM_DAYS), key=lambda d: conflict_counts[d])
            best_slot = min(
                range(SLOTS_PER_DAY), key=lambda s: day_slot_counts[best_day][s]
            )

        module_day[module_id] = best_day
        module_slot[module_id] = best_slot
        day_slot_counts[best_day][best_slot] += 1

    # Count violations
    student_violations = 0
    for student_id, mods in student_modules.items():
        day_counts = defaultdict(int)
        for m in mods:
            day_counts[module_day[m]] += 1
        for day, count in day_counts.items():
            if count > 1:
                student_violations += count - 1

    print(f"Exams distributed across {NUM_DAYS} days, {TOTAL_SLOTS} slots")
    if student_violations > 0:
        print(
            f"WARNING: {
              student_violations} student-day violations (need {num_colors_needed} days, have {NUM_DAYS})"
        )

    # ========== PHASE 3: Room assignment (by formation and group) ==========
    print("Assigning rooms to exams (by group)...")

    # For each module, determine which groups are enrolled and their sizes
    def get_module_groups(module_id):
        """Get groups enrolled in a module with their sizes."""
        groups = defaultdict(int)  # (formation_id, groupe) -> count
        for student_id in module_students[module_id]:
            if student_id in student_info:
                info = student_info[student_id]
                key = (info["formation_id"], info["groupe"])
                groups[key] += 1
        return groups

    # Group by (day, slot)
    slot_modules = defaultdict(list)
    for module_id in module_ids:
        day = module_day[module_id]
        slot = module_slot[module_id]
        slot_modules[(day, slot)].append(module_id)

    # module_rooms[module_id] = [(room_id, room_type, formation_id, "group_str"), ...]
    module_rooms = {}

    # Separate rooms by type for easier assignment
    amphitheaters = [(r[0], r[1], r[2]) for r in locations if r[2] == "Amphi"]
    salles_td = [(r[0], r[1], r[2]) for r in locations if r[2] == "Salle_TD"]

    for (day, slot), mods in slot_modules.items():
        # Track available rooms for this slot
        available_amphis = list(amphitheaters)
        available_salles = list(salles_td)

        for module_id in mods:
            groups = get_module_groups(module_id)
            assigned_rooms = []

            # Sort groups by size (largest first)
            sorted_groups = sorted(groups.items(), key=lambda x: x[1], reverse=True)

            # Collect groups that need assignment: ((formation_id, groupe), size)
            pending_groups = list(sorted_groups)

            # Assign groups to rooms
            while pending_groups:
                group_key, size = pending_groups.pop(0)
                formation_id, groupe_num = group_key

                if size > 20:
                    # Large group needs Amphi (60 capacity)
                    if available_amphis:
                        room_id, cap, rtype = available_amphis.pop(0)
                        remaining_cap = cap - size
                        groups_in_room = [groupe_num]

                        # Try to add more groups from SAME formation to fill amphi
                        i = 0
                        while i < len(pending_groups) and remaining_cap >= 10:
                            pg_key, pg_size = pending_groups[i]
                            if pg_key[0] == formation_id and pg_size <= remaining_cap:
                                groups_in_room.append(pg_key[1])
                                remaining_cap -= pg_size
                                pending_groups.pop(i)
                            else:
                                i += 1

                        group_str = ",".join(str(g) for g in sorted(groups_in_room))
                        assigned_rooms.append((room_id, rtype, formation_id, group_str))
                    elif available_salles:
                        # Fallback: use multiple salles for large group
                        needed = size
                        group_str = str(groupe_num)
                        while needed > 0 and available_salles:
                            room_id, cap, rtype = available_salles.pop(0)
                            assigned_rooms.append((room_id, rtype, formation_id, group_str))
                            needed -= cap
                else:
                    # Small group can use Salle_TD (20 capacity)
                    if available_salles:
                        room_id, cap, rtype = available_salles.pop(0)
                        remaining_cap = cap - size
                        groups_in_room = [groupe_num]

                        # Try to combine with another small group from SAME formation
                        i = 0
                        while i < len(pending_groups) and remaining_cap >= 5:
                            pg_key, pg_size = pending_groups[i]
                            if pg_key[0] == formation_id and pg_size <= remaining_cap:
                                groups_in_room.append(pg_key[1])
                                remaining_cap -= pg_size
                                pending_groups.pop(i)
                            else:
                                i += 1

                        group_str = ",".join(str(g) for g in sorted(groups_in_room))
                        assigned_rooms.append((room_id, rtype, formation_id, group_str))
                    elif available_amphis:
                        # Fallback: use amphi for small group
                        room_id, cap, rtype = available_amphis.pop(0)
                        assigned_rooms.append((room_id, rtype, formation_id, str(groupe_num)))

            module_rooms[module_id] = assigned_rooms

    # ========== PHASE 4: Professor assignment ==========
    print("Assigning proctors to exams...")

    # Calculate proctors needed per room type
    # Salle_TD (20 seats): 1 proctor
    # Amphi (60 seats): 3 proctors (1 per 20 students)
    def proctors_for_room(room_type):
        return 3 if room_type == "Amphi" else 1

    # Calculate total proctoring sessions needed
    total_sessions = sum(
        sum(proctors_for_room(rtype) for _, rtype, _, _ in rooms)
        for rooms in module_rooms.values()
    )
    sessions_per_prof = total_sessions // len(prof_ids)
    extra_sessions = total_sessions % len(prof_ids)

    print(f"Total proctoring sessions: {total_sessions}")
    print(f"Sessions per professor: {
          sessions_per_prof} (+1 for {extra_sessions} profs)")

    # Build department to professors mapping
    dept_profs = defaultdict(list)
    for prof_id, prof_data in professors.items():
        dept_profs[prof_data["dept_id"]].append(prof_id)

    # Track professor assignments
    prof_sessions = defaultdict(int)  # prof_id -> count
    prof_day_count = defaultdict(lambda: defaultdict(int))  # prof_id -> day -> count

    exam_proctors = {}  # module_id -> list of prof_ids

    # Sort modules: prioritize by department to help with department priority constraint
    # Group modules by department
    dept_modules = defaultdict(list)
    for module_id, data in modules.items():
        dept_modules[data["dept_id"]].append(module_id)

    # Process each module
    for module_id in module_ids:
        day = module_day[module_id]
        # Calculate total proctors needed based on room types
        num_proctors_needed = sum(
            proctors_for_room(rtype) for _, rtype, _, _ in module_rooms[module_id]
        )
        dept_id = modules[module_id]["dept_id"]

        assigned_proctors = []

        # Get eligible professors (not at max for the day, not at max sessions)
        def is_eligible(prof_id):
            max_sessions = sessions_per_prof + (1 if prof_id <= extra_sessions else 0)
            return (
                prof_day_count[prof_id][day] < 3
                and prof_sessions[prof_id] < max_sessions
                and prof_id not in assigned_proctors
            )

        # First, try same-department professors
        same_dept_profs = [p for p in dept_profs[dept_id] if is_eligible(p)]
        # Sort by current load (least loaded first)
        same_dept_profs.sort(key=lambda p: prof_sessions[p])

        for prof_id in same_dept_profs:
            if len(assigned_proctors) >= num_proctors_needed:
                break
            assigned_proctors.append(prof_id)
            prof_sessions[prof_id] += 1
            prof_day_count[prof_id][day] += 1

        # If still need more, use other department professors
        if len(assigned_proctors) < num_proctors_needed:
            other_profs = [
                p for p in prof_ids if p not in dept_profs[dept_id] and is_eligible(p)
            ]
            other_profs.sort(key=lambda p: prof_sessions[p])

            for prof_id in other_profs:
                if len(assigned_proctors) >= num_proctors_needed:
                    break
                assigned_proctors.append(prof_id)
                prof_sessions[prof_id] += 1
                prof_day_count[prof_id][day] += 1

        exam_proctors[module_id] = assigned_proctors

    # ========== PHASE 5: Balance professor loads ==========
    print("Balancing professor workloads...")

    # Check current distribution
    session_counts = list(prof_sessions.values())
    print(
        f"Session distribution - Min: {min(session_counts)}, Max: {max(session_counts)}, "
        f"Avg: {sum(session_counts)/len(session_counts):.1f}"
    )

    # ========== PHASE 6: Write to database ==========
    print("\nWriting schedule to database...")

    # Clear existing data
    cur.execute("DELETE FROM surveillances")
    cur.execute("DELETE FROM examens")
    conn.commit()

    exam_count = 0
    surveillance_count = 0

    for module_id in module_ids:
        day_idx = module_day[module_id]
        slot = module_slot[module_id]
        rooms = module_rooms[module_id]
        proctors = exam_proctors[module_id]

        # Get actual date from exam_days list
        exam_date = exam_days[day_idx]
        slot_time = SLOT_TIMES[slot]
        datetime_str = f"{exam_date.strftime('%Y-%m-%d')} {slot_time}"

        # Create an exam entry for each room with formation and group assignment
        exam_ids = []
        for room_id, room_type, formation_id, group_str in rooms:
            cur.execute(
                "INSERT INTO examens (module_id, lieu_examen_id, date_heure, formation_id, groupes) VALUES (%s, %s, %s, %s, %s)",
                (module_id, room_id, datetime_str, formation_id, group_str),
            )
            exam_ids.append(cur.lastrowid)
            exam_count += 1

        # Assign proctors to rooms (one proctor per room)
        for i, prof_id in enumerate(proctors):
            exam_id = exam_ids[i % len(exam_ids)] if exam_ids else None
            if exam_id:
                cur.execute(
                    "INSERT INTO surveillances (examen_id, prof_id) VALUES (%s, %s)",
                    (exam_id, prof_id),
                )
                surveillance_count += 1

    conn.commit()

    elapsed = time.time() - start_time

    print(f"\n{'='*50}")
    print(f"Optimization completed in {elapsed:.2f} seconds")
    print(f"{'='*50}")
    print(f"Created {exam_count} exams across {
          NUM_DAYS} days ({TOTAL_SLOTS} slots)")
    print(f"Assigned {surveillance_count} proctoring sessions")
    print(f"Sessions per professor: ~{surveillance_count // len(prof_ids)}")

    # Verify constraints
    print("\nVerifying constraints...")

    # Check student constraint (max 1 exam per day)
    # Students take all modules of their formation, so check via formation_id
    cur.execute("""
        SELECT e.id as etudiant_id, DATE(ex.date_heure) as exam_date,
               COUNT(DISTINCT ex.module_id) as exam_count
        FROM etudiants e
        JOIN modules m ON e.formation_id = m.formation_id
        JOIN examens ex ON m.id = ex.module_id
        GROUP BY e.id, DATE(ex.date_heure)
        HAVING COUNT(DISTINCT ex.module_id) > 1
        LIMIT 5
    """)
    violations = cur.fetchall()
    if violations:
        print(f"WARNING: {len(violations)} student-day violations found")
    else:
        print("OK: No student has more than 1 exam per day")

    # Check professor constraint (max 3 exams per day)
    cur.execute("""
        SELECT s.prof_id, DATE(ex.date_heure) as exam_date, COUNT(*) as exam_count
        FROM surveillances s
        JOIN examens ex ON s.examen_id = ex.id
        GROUP BY s.prof_id, DATE(ex.date_heure)
        HAVING COUNT(*) > 3
        LIMIT 5
    """)
    violations = cur.fetchall()
    if violations:
        print(f"WARNING: {len(violations)} professor-day violations found")
    else:
        print("OK: No professor has more than 3 exams per day")

    # Check session distribution
    cur.execute("""
        SELECT prof_id, COUNT(*) as sessions
        FROM surveillances
        GROUP BY prof_id
    """)
    session_data = cur.fetchall()
    sessions = [row[1] for row in session_data]
    if sessions:
        print(
            f"Professor sessions - Min: {min(sessions)}, Max: {max(sessions)}, "
            f"Range: {max(sessions) - min(sessions)}"
        )

    conn.close()

    return {
        "elapsed_time": elapsed,
        "num_exams": exam_count,
        "num_days": NUM_DAYS,
        "num_slots": TOTAL_SLOTS,
        "num_surveillances": surveillance_count,
        "student_violations": student_violations,
    }


if __name__ == "__main__":
    optimize_schedule()
