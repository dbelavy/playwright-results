#!/usr/bin/osascript

using terms from application "Messages"
    tell application "Messages"
        set allChats to chats
        repeat with aChat in allChats
            if id of aChat starts with "SMS" then
                log "SMS Chat: " & (id of aChat)
                set theMessages to messages of aChat
                repeat with eachMessage in theMessages
                    try
                        set theContent to content of eachMessage
                        set theSender to sender of eachMessage
                        log "From: " & theSender & ", Message: " & theContent
                    end try
                end repeat
            end if
        end repeat
    end tell
end using terms from
