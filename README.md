## **Command Reference**

### **1. Task Management**

#### **Create Tasks**
```bash
kd . Buy milk /grocery                      # Basic task
kd . "Team meeting" /work @meeting ^fri :n  # Note with tag and deadline
kd . Fix bug! /dev @urgent ^2h              # High-priority task, due 2 hours from now
```
- **`!`** = High priority
- **`/project`** = Assign project
- **`@tag`** = Add tag
- **`^deadline`** = Set deadline
- **`:n`** = Mark as note (instead of task)

### **2. Modify Tasks**
#### **Basic Edits**
```bash
kd .1 "New title" /newproject :n  # Update title, project, and mark as note
```
#### Tag Changes
```bash
kd .1 @tag       # Toggle tag
kd .1 @+tag      # Force-add tag
kd .1 @-tag      # Force-remove tag
```
#### **Status Changes**
```bash
kd .1 :done     # Mark done (or `:d`)
kd .1 :pending  # Mark pending (or `:p`)
kd .1 :note     # Convert to note (or `:n`)
kd .1 :         # Toggle done/pending
```
#### **Priority Adjustments**
```bash
kd .1 !          # Toggle high/normal
kd .1 !high      # Set high priority
kd .1 !normal    # Set normal priority
kd .1 !low       # Set low priority
kd .1 !+         # Increase priority
kd .1 !-         # Decrease priority
```

### **3. Deadlines**
#### **Relative Adjustments**
```bash
kd .1 ^+3d      # Postpone 3 days
kd .1 ^+1w2h    # Postpone 1 week 2 hours
kd .1 ^-6h      # Move earlier by 6 hours
```
#### **Absolute Deadlines**
```bash
kd .1 ^mon            # Next Monday
kd .1 ^2tue           # Tuesday after next
kd .1 ^today          # Due today
kd .1 ^never          # Remove deadline
kd .1 ^"5 Aug 2025"   # Set specific date
```

### **4. Delete Tasks**
```bash
kd -.1          # Delete task 1
kd -.1-5        # Delete tasks 1–5
```
*(Note: `-.1` deletes, while `.-1` modifies the last task.)*

### **5. Filter & Search**
#### **Basic Filters**
```bash
kd 1-5          # Show tasks 1–5
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

### **6. Bulk Operations**
#### **Multi-Task Edits**
```bash
kd .1,3 .4,5-7 :done    # Mark multiple tasks done
kd /home !high          # Set all "home" tasks to high priority
```
#### **Selection and Action Disambiguation**
```bash
kd /old -> /new         # Rename project
kd .1-4 "^fix" @old -> @old @new  # Replace @old tag with @new for tasks 1–4 with title starting with "fix" and has tag "@old"
```
*(`->` separates selection from action but is optional for single operations.)*

## **Quick Symbol Guide**

| Symbol | Meaning          | Example           |
|--------|------------------|-------------------|
| `.`    | Task modifier    | `kd .1 :done`     |
| `/`    | Project          | `/work`           |
| `@`    | Tag              | `@important`      |
| `^`    | Deadline         | `^tomorrow`       |
| `:`    | Status           | `:pending`        |
| `!`    | Priority         | `!high`           |
| `-`    | Delete           | `-.1`             |
| `=`    | Sort-by          | `=/`              |
| `->`   | Separator        | `kd /old -> /new` |

