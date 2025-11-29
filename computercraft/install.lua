-- ComputerCraft Item Transporter Installation Script
-- Run this script to download and set up the transporter

local SERVER_URL = "https://dynamices.nl:7781"  -- Server URL
local TRANSPORTER_URL = SERVER_URL .. "/static/transporter.lua"  -- Adjust path as needed

print("ComputerCraft Item Transporter Installer")
print("========================================")
print()

-- Function to download file
local function downloadFile(url, filename)
    print("Downloading " .. filename .. " from " .. url .. "...")
    
    -- Use http.request with insecure option to skip SSL verification
    local response = http.request({
        url = url,
        method = "GET",
        insecure = true  -- Skip SSL certificate verification (needed for some HTTPS setups)
    })
    
    if not response then
        print("ERROR: Could not download file from " .. url)
        return false
    end
    
    local content = response.readAll()
    response.close()
    
    local file = fs.open(filename, "w")
    if not file then
        print("ERROR: Could not create file " .. filename)
        return false
    end
    
    file.write(content)
    file.close()
    
    print("Downloaded " .. filename .. " successfully!")
    return true
end

-- Function to create startup script
local function createStartup()
    print("Creating startup script...")
    
    local startupContent = [[
-- Auto-start transporter
shell.run("transporter")
]]
    
    local file = fs.open("startup", "w")
    if file then
        file.write(startupContent)
        file.close()
        print("Startup script created!")
        return true
    else
        print("WARNING: Could not create startup script")
        return false
    end
end

-- Main installation
print("This script will:")
print("1. Download transporter.lua")
print("2. Set up configuration")
print("3. Create startup script")
print()

-- Get API key from user
print("Please enter your API key:")
print("(You can get this from the web dashboard)")
write("API Key: ")
local apiKey = read()

if not apiKey or apiKey == "" then
    print("ERROR: API key is required!")
    return
end

-- Get machine name
print()
print("Enter a name for this machine (or press Enter for default):")
write("Machine Name [Computer]: ")
local machineName = read()
if machineName == "" then
    machineName = "Computer"
end

-- Download transporter
print()
if not downloadFile(TRANSPORTER_URL, "transporter.lua") then
    print()
    print("NOTE: Could not download from server.")
    print("You may need to manually copy transporter.lua to this computer.")
    print("Press any key to continue with configuration...")
    os.pullEvent("key")
end

-- Create configuration
print()
print("Creating configuration...")
local config = {
    server_url = SERVER_URL,
    api_key = apiKey,
    machine_name = machineName,
    poll_interval = 5,
    retry_delay = 2,
    max_retries = 3
}

local configFile = fs.open("transporter_config", "w")
if configFile then
    configFile.write(textutils.serialize(config))
    configFile.close()
    print("Configuration saved!")
else
    print("ERROR: Could not save configuration")
    return
end

-- Create startup script
print()
createStartup()

-- Final instructions
print()
print("========================================")
print("Installation complete!")
print()
print("Configuration:")
print("  Server URL: " .. SERVER_URL)
print("  Machine Name: " .. machineName)
print("  API Key: " .. string.sub(apiKey, 1, 10) .. "...")
print()
print("To start the transporter, run:")
print("  transporter")
print()
print("Or restart this computer to auto-start.")
print("========================================")

