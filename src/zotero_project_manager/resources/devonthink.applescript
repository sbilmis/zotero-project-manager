use framework "Foundation"
use scripting additions

-- One script is shared by the CLI and the Zotero plugin. JSON values are data.
on run argv
    set jsonData to current application's NSData's dataWithContentsOfFile:(item 1 of argv)
    set plan to current application's NSJSONSerialization's JSONObjectWithData:jsonData options:0 |error|:(missing value)
    if plan is missing value then error "Could not read the prepared source list."
    set workspacePath to (plan's objectForKey:"workspace") as text
    if my isTemporary(workspacePath) then error "DEVONthink copies temporary files instead of indexing them. Export to a permanent folder, such as ResearchProjects, and try again."
    set groupID to item 2 of argv
    set workspaceName to (plan's objectForKey:"name") as text
    set indexedCount to 0
    set reusedCount to 0
    -- DT3 shares the legacy DNtp signature. Use DT4's distinct bundle ID only.
    tell application id "com.devon-technologies.think"
        if (version as text) does not start with "4." then error "This handoff requires DEVONthink 4. No files were linked."
        activate
        if (count of databases) is 0 then error "Open a DEVONthink 4 database, then try again."
        if groupID is "" then
            set destinationGroup to display group selector "Choose where to link the exported Zotero collection"
            if destinationGroup is missing value then return "Cancelled; your exported files are unchanged."
        else
            set destinationGroup to get record with uuid groupID
            if destinationGroup is missing value then error "The DEVONthink destination group could not be found. Open its database first."
            if type of destinationGroup is not group then error "The DEVONthink destination must be a group."
        end if
        set targetDatabase to database of destinationGroup
        if read only of targetDatabase then error "Choose a writable DEVONthink database."
        repeat with entry in (plan's objectForKey:"files")
            set filePath to (entry's objectForKey:"path") as text
            set relativePath to (entry's objectForKey:"relative") as text
            set matches to lookup records with path filePath in targetDatabase
            set alreadyLinked to false
            repeat with candidate in matches
                if (indexed of candidate) and (path of candidate) is filePath then
                    if not (synchronize record candidate) then error "DEVONthink could not refresh " & filePath
                    set alreadyLinked to true
                    exit repeat
                end if
            end repeat
            if alreadyLinked then
                set reusedCount to reusedCount + 1
            else
                set parentPath to my parentLocation(workspaceName, relativePath)
                set targetGroup to create location parentPath in destinationGroup
                set linkedRecord to indicate filePath to targetGroup
                if linkedRecord is missing value then error "DEVONthink could not index " & filePath
                if not (indexed of linkedRecord) then error "DEVONthink made a copy instead of an index link. Check the destination group before retrying with a permanent export folder."
                set indexedCount to indexedCount + 1
            end if
        end repeat
    end tell
    return "Linked " & indexedCount & " files to DEVONthink 4; " & reusedCount & " already present in this database. Re-run Send to DEVONthink 4 to add newly exported files."
end run

on parentLocation(workspaceName, relativePath)
    set components to (current application's NSString's stringWithString:relativePath)'s pathComponents() as list
    set locationPath to "/" & my escapeComponent(workspaceName)
    if (count of components) > 1 then
        repeat with indexNumber from 1 to ((count of components) - 1)
            set locationPath to locationPath & "/" & my escapeComponent(item indexNumber of components)
        end repeat
    end if
    return locationPath
end parentLocation

on escapeComponent(value)
    set value to current application's NSString's stringWithString:value
    return (value's stringByReplacingOccurrencesOfString:"/" withString:"\\/") as text
end escapeComponent

on isTemporary(value)
    set normalized to (current application's NSString's stringWithString:value)'s stringByResolvingSymlinksInPath()
    set temporaryRoots to {current application's NSTemporaryDirectory() as text, "/tmp", "/private/tmp"}
    repeat with temporaryRoot in temporaryRoots
        set rootPath to ((current application's NSString's stringWithString:temporaryRoot)'s stringByResolvingSymlinksInPath()) as text
        if (normalized as text) is rootPath then return true
        if (normalized's hasPrefix:(rootPath & "/")) as boolean then return true
    end repeat
    return false
end isTemporary
