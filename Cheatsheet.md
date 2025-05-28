## **Command Reference**

### **1 . Task Management**

#### **Create Tasks**
```bash
tusk . Buy milk /grocery                      # Basic task
tusk . "Team meeting" /work @meeting ^fri ,n  # Note with tag and deadline
tusk . Fix bug! /dev @urgent ^2h              # High-priority task, due 2 hours from now
```
- **`.`** separates selection from action,
  empty selection means we are modifying a new task.
- **`!`** = High priority
- **`/project`** = Assign project
- **`@tag`** = Add tag
- **`^deadline`** = Set deadline
- **`,n`** = Mark as note (instead of task)

### **2. Modify Tasks**
#### **Basic Edits**
```bash
tusk 1 . New title /newproject ,n  # Update title, project, and mark as note for task 1
```
#### Tag Changes
```bash
tusk 1 . @tag       # Toggle tag
tusk 1 . @+tag      # Force-add tag
tusk 1 . @-tag      # Force-remove tag
```
#### **Status Changes**
```bash
tusk 1 . ,done     # Mark done (or `,d`)
tusk 1 . ,pending  # Mark pending (or `,p`)
tusk 1 . ,note     # Convert to note (or `,n`)
tusk 1 . ,         # Toggle done/pending
```
#### **Priority Adjustments**
```bash
tusk 1 . !          # Toggle high/normal
tusk 1 . !high      # Set high priority
tusk 1 . !normal    # Set normal priority
tusk 1 . !low       # Set low priority
tusk 1 . !+         # Increase priority
tusk 1 . !-         # Decrease priority
```

### **3. Deadlines**
#### **Relative Adjustments**
```bash
tusk 1 . ^+3d     # Postpone 3 days
tusk 1 . ^+1w2h   # Postpone 1 week 2 hours
tusk 1 . ^-6h     # Move earlier by 6 hours
```
#### **Absolute Deadlines**
```bash
tusk 1 . ^mon             # Next Monday
tusk 1 . ^2tue            # Tuesday after next
tusk 1 . ^today           # Due today
tusk 1 . "^tomorrow 8pm"  # Due tomorrow at 8 PM
tusk 1 . ^never           # Remove deadline
tusk 1 . ^"25-8-5 9:00"   # Set specific date and time
```

### **4. Delete Tasks**
```bash
tusk 1..5 . ,x    # Delete tasks 1-5
tusk ,done . ,x   # Delete all done tasks
```

### **5. Filter & Search**
#### **Basic Filters**
```bash
tusk 1..5       # Show tasks 1-5
tusk /work      # Tasks in "work" project
tusk @meeting   # Tasks with "@meeting" tag
tusk !high      # High-priority tasks
tusk ,pending   # Pending tasks
tusk ^today     # Due today
tusk ^w         # Due by the end of this week
tusk ^+1d       # Due in 24 hours
tusk ^-1d ^oo   # Due 24 hours ago or later
```
#### **Grouping/Sorting**
```bash
tusk /    # Group by project
tusk @    # Group by tag (can have duplicate items across groups)
tusk !    # Group by priority
tusk ^    # Group by deadline
tusk =/   # Sort by project names
tusk =@   # Sort by tag names
tusk =!   # Sort by priorities
tusk =^   # Sort by deadlines
```
#### **Advanced Search**
```bash
tusk /work !high ^today           # High-priority work tasks due today
```

### **6. Edit Multiple Tasks**
```bash
tusk 1 3 4 6..9 . ,done       # Mark multiple tasks done
tusk /home . !high            # Set all "home" tasks to high priority
tusk /old . /new              # Rename project
tusk 1..4 @old . @-old @+new  # Replace @old tag with @new for tasks 1-4 with title starting with "fix" and has tag "@old"
tusk 2..5 . ,x                # delete tasks 2-5
```

## **Quick Symbol Guide**

| Symbol | Name      | Example Usage   |
|--------|-----------|-----------------|
| `.`    | Separator | `/old . /new`   |
| `..`   | ID Range  | `2..5`          |
| `/`    | Project   | `/work`         |
| `@`    | Tag       | `@bug`          |
| `^`    | Deadline  | `^tomorrow`     |
| `,`    | Status    | `,pending`      |
| `!`    | Priority  | `!high`         |
| `,x`   | Delete    | `,done . ,x`    |
| `=`    | Sort-by   | `=/`            |

