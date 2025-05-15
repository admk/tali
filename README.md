## **Command Reference**

### **1 . Task Management**

#### **Create Tasks**
```bash
kd . Buy milk /grocery                      # Basic task
kd . "Team meeting" /work @meeting ^fri :n  # Note with tag and deadline
kd . Fix bug! /dev @urgent ^2h              # High-priority task, due 2 hours from now
```
- **`.`** separates selection from action,
  empty selection means we are modifying a new task.
- **`!`** = High priority
- **`/project`** = Assign project
- **`@tag`** = Add tag
- **`^deadline`** = Set deadline
- **`:n`** = Mark as note (instead of task)

### **2. Modify Tasks**
#### **Basic Edits**
```bash
kd 1 . New title /newproject :n  # Update title, project, and mark as note for task 1
```
- The space surrounding `.` can be omitted.
#### Tag Changes
```bash
kd 1 . @tag       # Toggle tag
kd 1 . @+tag      # Force-add tag
kd 1 . @-tag      # Force-remove tag
```
#### **Status Changes**
```bash
kd 1 . :done     # Mark done (or `:d`)
kd 1 . :pending  # Mark pending (or `:p`)
kd 1 . :note     # Convert to note (or `:n`)
kd 1 . :         # Toggle done/pending
```
#### **Priority Adjustments**
```bash
kd 1 . !          # Toggle high/normal
kd 1 . !high      # Set high priority
kd 1 . !normal    # Set normal priority
kd 1 . !low       # Set low priority
kd 1 . !+         # Increase priority
kd 1 . !-         # Decrease priority
```

### **3. Deadlines**
#### **Relative Adjustments**
```bash
kd 1 . ^+3d      # Postpone 3 days
kd 1 . ^+1w2h    # Postpone 1 week 2 hours
kd 1 . ^-6h      # Move earlier by 6 hours
```
#### **Absolute Deadlines**
```bash
kd 1 . ^mon             # Next Monday
kd 1 . ^2tue            # Tuesday after next
kd 1 . ^today           # Due today
kd 1 . ^tomorrow ^8pm   # Due tomorrow at 8 PM
kd 1 . ^never           # Remove deadline
kd 1 . ^"25-8-5" ^9:00  # Set specific date and time
```

### **4. Delete Tasks**
```bash
kd 1..5 . -   # Delete tasks 1–5
kd :done . -  # Delete all done tasks
```

### **5. Filter & Search**
#### **Basic Filters**
```bash
kd 1..5          # Show tasks 1–5
kd /work        # Tasks in "work" project
kd @meeting     # Tasks with "@meeting" tag
kd !high        # High-priority tasks
kd :pending     # Pending tasks
kd ^today       # Due today
```
#### **Grouping/Sorting**
```bash
kd /            # Group by project
kd @            # Group by tag
kd !            # Group by priority
kd ^            # Group by deadline
kd =/           # Sort by project names
kd =@           # Sort by tag names
kd =!           # Sort by priorities
kd =^           # Sort by deadlines
```
#### **Advanced Search**
```bash
kd "fix (bug|issue)" @critical  # Search regex + tag
kd /work !high ^today           # High-priority work tasks due today
```

### **6. Edit Multiple Tasks**
```bash
kd 1 3 4 6..9 . :done       # Mark multiple tasks done
kd /home . !high            # Set all "home" tasks to high priority
kd /old . /new              # Rename project
kd 1..4 @old . @-old @+new  # Replace @old tag with @new for tasks 1–4 with title starting with "fix" and has tag "@old"
kd 2..5 . --                # delete tasks 2–5
```

## **Quick Symbol Guide**

| Symbol | Name      | Example Usage   |
|--------|-----------|-----------------|
| `.`    | Separator | `/old . /new`   |
| `..`   | ID Range  | `2..5`          |
| `/`    | Project   | `/work`         |
| `@`    | Tag       | `@bug`          |
| `^`    | Deadline  | `^tomorrow`     |
| `:`    | Status    | `:pending`      |
| `!`    | Priority  | `!high`         |
| `-`    | Delete    | `:done . -`     |
| `=`    | Sort-by   | `=/`            |

