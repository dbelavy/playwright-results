-- AppleScript to process only SMS messages from "msverify" and extract six-digit codes

-- Function to extract a six-digit verification code using regex
on extractCode(messageText)
    set regexPattern to "\\b\\d{6}\\b" -- Match exactly 6 digits
    try
        do shell script "echo " & quoted form of messageText & " | grep -oE " & quoted form of regexPattern
    on error
        return "No code found"
    end try
end extractCode

-- Main script to process incoming SMS messages from "msverify"
tell application "Messages"
    set targetService to 1st service whose service type = SMS -- Filter only SMS chats
    set targetChats to chats of targetService -- Get all chats for SMS service

    repeat with targetChat in targetChats
        try
            -- Process only chats where the sender is "msverify"
            set chatName to name of targetChat
            if chatName = "msverify" then
                -- Get messages for the chat
                set recentMessages to messages of targetChat
                if (count of recentMessages) > 0 then
                    -- Get the last message in the chat
                    set lastMessage to last item of recentMessages
                    if direction of lastMessage is incoming then -- Only process incoming messages
                        set messageText to text of lastMessage
                        if messageText contains "Use verification code" then
                            -- Extract the six-digit code
                            set verificationCode to extractCode(messageText)
                            -- Display the extracted code
                            display dialog "Verification Code Found: " & verificationCode
                        end if
                    end if
                end if
            end if
        on error errMsg
            -- Log errors to the console for debugging
            log "Error processing chat: " & errMsg
        end try
    end repeat
end tell