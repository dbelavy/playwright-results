#!/usr/bin/osascript

using terms from application "Messages"
    on messagesReceived(theMessages)
        repeat with eachMessage in theMessages
            try
                set theSender to sender of eachMessage
                set theContent to content of eachMessage
                log "From: " & theSender & ", Message: " & theContent
            end try
        end repeat
    end messagesReceived
end using terms from
