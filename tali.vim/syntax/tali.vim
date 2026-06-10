" Vim syntax file for Tali task manager commands
if exists("b:current_syntax")
  finish
endif

" Comments (# ... till end of line)
syn match taliComment "\v#.*$"

" Task range (e.g., 42, 1..5)
syn match taliTaskRange "\v<\d+>"
syn match taliTaskRange "\v<\d+\.\.\d+>"

" Project (e.g., /work, /home/grocery)
syn match taliProject "\v\/[a-zA-Z0-9_\-/]*"

" Tag (e.g., @star, @+urgent)
syn match taliTag "\v\@[+\-]?[a-zA-Z0-9_\-]*"

" Deadline (e.g., ^today, ^"tue 4pm")
syn match taliDeadline "\v\^\S*"
syn region taliDeadline start=/\v\^"/ skip=/\v\\./ end=/\v"/
syn region taliDeadline start=/\v\^'/ skip=/\v\\./ end=/\v'/

" Priority (e.g., !high, !)
syn match taliPriority "\v!\S*"
syn region taliPriority start=/\v!"/ skip=/\v\\./ end=/\v"/
syn region taliPriority start=/\v!'/ skip=/\v\\./ end=/\v'/

" Status (e.g., ,n, ,done)
syn match taliStatus "\v,\S*"
syn region taliStatus start=/\v,"/ skip=/\v\\./ end=/\v"/
syn region taliStatus start=/\v,'/ skip=/\v\\./ end=/\v'/

" Description (e.g., : description text)
syn match taliDescription "\v:\s[^#]*"

" Sort operator (e.g., =^, =@)
syn match taliSort "\v\=([?/@!,^:]|\.\.)"

" Query operator (e.g., ?^, ?@)
syn match taliQuery "\v\?([?/@!,^:]|\.\.)"

" Separator (dot between commands)
syn match taliSeparator "\v\." contained

" Highlight groups
hi def link taliComment     Comment
hi def link taliTaskRange   Special
hi def link taliProject     Identifier
hi def link taliTag         Type
hi def link taliDeadline    PreProc
hi def link taliPriority    Statement
hi def link taliStatus      Constant
hi def link taliDescription String
hi def link taliSort        Operator
hi def link taliQuery       Question
hi def link taliSeparator   Delimiter

let b:current_syntax = "tali"
