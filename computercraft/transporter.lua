-- ComputerCraft Item Transporter
-- Connects to Flask server and executes item transport routes

local config = {
    server_url = "http://dynamices.nl:7781",
    api_key = "",
    machine_name = "Computer",
    poll_interval = 5, -- seconds
    retry_delay = 2, -- seconds
    max_retries = 3
}

-- Load configuration from file if it exists
local function loadConfig()
    if fs.exists("transporter_config") then
        local file = fs.open("transporter_config", "r")
        local content = file.readAll()
        file.close()
        local success, data = pcall(textutils.unserialize, content)
        if success and data then
            for k, v in pairs(data) do
                config[k] = v
            end
        end
    end
end

-- Save configuration to file
local function saveConfig()
    local file = fs.open("transporter_config", "w")
    file.write(textutils.serialize(config))
    file.close()
end

-- HTTP request helper
local function httpRequest(method, endpoint, data)
    local url = config.server_url .. endpoint
    local headers = {
        ["Content-Type"] = "application/json",
        ["X-API-Key"] = config.api_key
    }
    
    local body = nil
    if data then
        body = textutils.serializeJSON(data)
    end
    
    local response = http.request({
        url = url,
        method = method,
        headers = headers,
        body = body
    })
    
    -- Check if response is valid (not a boolean false)
    if response and type(response) == "table" then
        local statusCode = response.getResponseCode()
        local responseBody = response.readAll()
        response.close()
        
        if statusCode == 200 then
            local success, result = pcall(textutils.unserializeJSON, responseBody)
            if success then
                return result, statusCode
            end
        end
        return nil, statusCode
    end
    
    return nil, 500
end

-- Authenticate with server
local function authenticate()
    local data, code = httpRequest("POST", "/api/auth", {
        name = config.machine_name
    })
    
    if code == 200 and data then
        return data.machine_id
    end
    
    return nil
end

-- Register peripherals with server
local function registerPeripherals(machineId)
    local peripherals = {}
    
    -- Get all peripheral names
    local sides = {"top", "bottom", "left", "right", "front", "back"}
    for _, side in ipairs(sides) do
        if peripheral.isPresent(side) then
            local periph = peripheral.wrap(side)
            if periph then
                local periphType = peripheral.getType(side)
                table.insert(peripherals, {
                    name = side,
                    type = periphType,
                    location = side
                })
            end
        end
    end
    
    -- Also check for Create mod specific peripherals
    -- Create mod peripherals might be accessed differently
    -- This is a basic implementation
    
    if #peripherals > 0 then
        local data, code = httpRequest("POST", "/api/peripherals", {
            machine_id = machineId,
            peripherals = peripherals
        })
        
        return code == 200
    end
    
    return false
end

-- Get transport commands from server
local function getCommands(machineId)
    local data, code = httpRequest("GET", "/api/commands?machine_id=" .. machineId, nil)
    
    if code == 200 and data and data.commands then
        return data.commands
    end
    
    return {}
end

-- Transfer items between peripherals
local function transferItems(sourceName, destName, itemFilter, itemNames)
    local source = peripheral.wrap(sourceName)
    local dest = peripheral.wrap(destName)
    
    if not source or not dest then
        print("Error: Could not wrap peripherals " .. sourceName .. " -> " .. destName)
        return false
    end
    
    -- Check if source has list() method (inventory)
    local sourceList = nil
    if source.list then
        sourceList = source.list()
    elseif source.getItems then
        -- Some Create mod peripherals might use getItems()
        sourceList = source.getItems()
    end
    
    if not sourceList then
        print("Error: Source peripheral does not support item listing")
        return false
    end
    
    local transferred = false
    
    -- Iterate through items in source
    for slot, item in pairs(sourceList) do
        if item then
            local itemName = item.name
            local shouldTransfer = false
            
            -- Check item filter
            if itemFilter then
                -- Simple string matching for now
                if string.find(itemName, itemFilter) then
                    shouldTransfer = true
                end
            elseif itemNames and #itemNames > 0 then
                -- Check if item is in the allowed list
                for _, allowedItem in ipairs(itemNames) do
                    if itemName == allowedItem then
                        shouldTransfer = true
                        break
                    end
                end
            else
                -- No filter, transfer all
                shouldTransfer = true
            end
            
            if shouldTransfer then
                -- Try to transfer items
                local count = item.count
                
                -- Use pushItems if available (standard inventory)
                if source.pushItems then
                    local transferredCount = source.pushItems(destName, slot, count)
                    if transferredCount > 0 then
                        transferred = true
                        print("Transferred " .. transferredCount .. "x " .. itemName .. " from " .. sourceName .. " to " .. destName)
                    end
                -- Try pullItems on destination (alternative method)
                elseif dest.pullItems then
                    local transferredCount = dest.pullItems(sourceName, slot, count)
                    if transferredCount > 0 then
                        transferred = true
                        print("Transferred " .. transferredCount .. "x " .. itemName .. " from " .. sourceName .. " to " .. destName)
                    end
                -- Create mod specific methods
                elseif source.transferTo then
                    local success = source.transferTo(dest, slot, count)
                    if success then
                        transferred = true
                        print("Transferred " .. count .. "x " .. itemName .. " from " .. sourceName .. " to " .. destName)
                    end
                else
                    print("Warning: No transfer method available for " .. sourceName .. " -> " .. destName)
                end
            end
        end
    end
    
    return transferred
end

-- Execute a transport command
local function executeCommand(command)
    if command.action == "transfer" then
        return transferItems(
            command.source,
            command.dest,
            command.item_filter,
            command.item_names
        )
    end
    
    return false
end

-- Update machine status
local function updateStatus(machineId, status)
    httpRequest("POST", "/api/status", {
        machine_id = machineId,
        status = status
    })
end

-- Main loop
local function main()
    print("ComputerCraft Item Transporter Starting...")
    print("Server: " .. config.server_url)
    
    -- Load configuration
    loadConfig()
    
    -- Check if API key is set
    if config.api_key == "" then
        print("ERROR: API key not set!")
        print("Please set your API key in transporter_config or run install.lua")
        return
    end
    
    -- Authenticate
    print("Authenticating with server...")
    local machineId = nil
    local retries = 0
    
    while not machineId and retries < config.max_retries do
        machineId = authenticate()
        if not machineId then
            retries = retries + 1
            print("Authentication failed, retrying... (" .. retries .. "/" .. config.max_retries .. ")")
            sleep(config.retry_delay)
        end
    end
    
    if not machineId then
        print("ERROR: Could not authenticate with server")
        return
    end
    
    print("Authenticated! Machine ID: " .. machineId)
    
    -- Register peripherals
    print("Registering peripherals...")
    registerPeripherals(machineId)
    
    -- Main polling loop
    print("Starting transport loop...")
    local pollCount = 0
    while true do
        local success, err = pcall(function()
            -- Update status every poll
            local statusData, statusCode = httpRequest("POST", "/api/status", {
                machine_id = machineId,
                status = "online"
            })
            
            if statusCode ~= 200 then
                print("Warning: Failed to update status (code: " .. tostring(statusCode) .. ")")
            end
            
            -- Get commands
            local commands = getCommands(machineId)
            
            if commands and #commands > 0 then
                print("Received " .. #commands .. " command(s)")
            end
            
            -- Execute commands
            for _, command in ipairs(commands) do
                executeCommand(command)
            end
            
            -- Re-register peripherals periodically (every 10 polls)
            pollCount = pollCount + 1
            if pollCount >= 10 then
                pollCount = 0
                print("Re-registering peripherals...")
                registerPeripherals(machineId)
            end
        end)
        
        if not success then
            print("Error in main loop: " .. tostring(err))
            -- Try to update status as offline on error
            pcall(function()
                updateStatus(machineId, "error")
            end)
        end
        
        sleep(config.poll_interval)
    end
end

-- Run main function
main()

