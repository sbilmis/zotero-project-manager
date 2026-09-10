use framework "Foundation"
use scripting additions

on run argv
    set jsonData to current application's NSData's dataWithContentsOfFile:(item 1 of argv)
    set plan to current application's NSJSONSerialization's JSONObjectWithData:jsonData options:0 |error|:(missing value)
    if plan is missing value then error "Could not read the prepared source list."
    set preparedFiles to {}
    repeat with entry in (plan's objectForKey:"files")
        set filePath to (entry's objectForKey:"path") as text
        set end of preparedFiles to POSIX file filePath as alias
    end repeat
    if (count of preparedFiles) > 0 then
        tell application "Finder"
            -- Finder needs file references, not aliases, for a multi-file selection.
            set finderFiles to {}
            repeat with preparedFile in preparedFiles
                set end of finderFiles to (get item (preparedFile as text))
            end repeat
            reveal item 1 of preparedFiles
            activate
            -- Opening a new folder is asynchronous; wait until the selection sticks.
            repeat 20 times
                delay 0.1
                set selection to finderFiles
                delay 0.1
                set selectedFiles to selection as alias list
                set selectionMatches to (count of selectedFiles) is (count of preparedFiles)
                repeat with preparedFile in preparedFiles
                    if (preparedFile as alias) is not in selectedFiles then set selectionMatches to false
                end repeat
                if selectionMatches then return "Prepared files selected in Finder."
            end repeat
            error "Finder opened the source folder but could not select every prepared file."
        end tell
    end if
    return "Prepared files selected in Finder."
end run
