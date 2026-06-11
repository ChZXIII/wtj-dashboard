import subprocess
import sys

def setup_notes():
    applescript = '''
    tell application "Notes"
        -- Check root folder "WTJ"
        if not (exists folder "WTJ") then
            make new folder with properties {name:"WTJ"}
            delay 0.5
        end if
        set rootFolder to folder "WTJ"
        
        -- Check "Facebook" folder under "WTJ"
        if not (exists folder "Facebook" of rootFolder) then
            make new folder with properties {name:"Facebook"} at rootFolder
            delay 0.5
        end if
        set fbFolder to folder "Facebook" of rootFolder
        
        -- Check and create subfolders based on content queues (Alternative A)
        set subfolders to {"1_Drafts", "2_Approved", "3_Published"}
        set queueFolders to {"FB_Videos_3-5Min", "Reels_Under1Min", "Text_Posts"}
        
        repeat with qFolder in queueFolders
            if not (exists folder qFolder of fbFolder) then
                make new folder with properties {name:qFolder} at fbFolder
                delay 0.2
            end if
            set parentQueue to folder qFolder of fbFolder
            repeat with subName in subfolders
                if not (exists folder subName of parentQueue) then
                    make new folder with properties {name:subName} at parentQueue
                    delay 0.1
                end if
            end repeat
        end repeat
    end tell
    '''
    
    process = subprocess.Popen(['osascript', '-e', applescript], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = process.communicate()
    
    if err:
        print(f"❌ Error setting up Apple Notes: {err.decode('utf-8')}")
        return False
    else:
        print("✅ Apple Notes folders set up successfully for queue structure!")
        print("   Structure created: WTJ -> Facebook -> [FB_Videos_3-5Min, Reels_Under1Min, Text_Posts] -> [1_Drafts, 2_Approved, 3_Published]")
        return True

if __name__ == "__main__":
    setup_notes()
