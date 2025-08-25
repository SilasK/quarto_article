--------------------------------------------------------------------------------
-- Copyright © 2021 Takuro Hosomi
-- This library is free software; you can redistribute it and/or modify it
-- under the terms of the MIT license. See LICENSE for details.
--------------------------------------------------------------------------------


--------------------------------------------------------------------------------
-- Global variables --
--------------------------------------------------------------------------------
base_url = "http://api.crossref.org"
mailto = "pandoc.doi2cite@gmail.com"
bibname = "fromDOI.bib"
key_list = {};
doi_key_map = {};
doi_entry_map = {};
error_strs = {};
error_strs["Resource not found."] = 404
error_strs["No acceptable resource available."] = 406
error_strs["<html><body><h1>503 Service Unavailable</h1>\n"
.. "No server is available to handle this request.\n"
.. "</body></html>"] = 503


--------------------------------------------------------------------------------
-- Pandoc Functions --
--------------------------------------------------------------------------------
-- Get bibliography filepath from yaml metadata
function Meta(m)
    local bib_data = m.bibliography
    local bibpaths = get_paths_from(bib_data)
    bibpath = find_filepath(bibname, bibpaths)
    bibpath = verify_path(bibpath)
    local f = io.open(bibpath, "r")
    if f then
        entries_str = f:read('*all')
        if entries_str then
            print("doi2cite: Reading " .. bibpath .. " (" .. #entries_str .. " bytes)")
            doi_entry_map = get_doi_entry_map(entries_str)
            doi_key_map = get_doi_key_map(entries_str)
            local count = 0
            for _ in pairs(doi_key_map) do
                count = count + 1
            end
            print("doi2cite: Loaded " .. count .. " cached DOIs")
            for doi, key in pairs(doi_key_map) do
                key_list[key] = true
            end
        end
        f:close()
    else
        make_new_file(bibpath)
    end
end

-- Get bibtex data of doi-based citation.id and make bibliography.
-- Then, replace "citation.id"
function Cite(c)
    for _, citation in pairs(c.citations) do
        local id = citation.id:gsub('%s+', ''):gsub('%%2F', '/')
        if id:sub(1, 16) == "https://doi.org/" then
            doi = id:sub(17):lower()
        elseif id:sub(1, 8) == "doi.org/" then
            doi = id:sub(9):lower()
        elseif id:sub(1, 4) == "DOI:" or id:sub(1, 4) == "doi:" then
            doi = id:sub(5):lower()
        else
            doi = nil
        end
        if doi then
            if doi_key_map[doi] then
                citation.id = doi_key_map[doi]
            else
                local entry_str = get_bibentry(doi)
                if entry_str == nil or error_strs[entry_str] then
                    print("Failed to get ref from DOI: " .. doi)
                else
                    entry_str = tex2raw(entry_str)
                    local entry_key = get_entrykey(entry_str)
                    if key_list[entry_key] then
                        entry_key = entry_key .. "_" .. doi
                        entry_str = replace_entrykey(entry_str, entry_key)
                    end
                    key_list[entry_key] = true
                    doi_key_map[doi] = entry_key
                    citation.id = entry_key
                    local f = io.open(bibpath, "a+")
                    if f then
                        f:write(entry_str .. "\n")
                        f:close()
                    else
                        error("Unable to open file: " .. bibpath)
                    end
                end
            end
        end
    end
    return c
end

--------------------------------------------------------------------------------
-- Common Functions --
--------------------------------------------------------------------------------
-- Get bib of DOI from http://api.crossref.org
function get_bibentry(doi)
    local entry_str = doi_entry_map[doi]
    if entry_str == nil then
        print("Requesting DOI: " .. doi)
        local url = base_url .. "/works/" .. doi .. "/transform/application/x-bibtex" .. "?mailto=" .. mailto
        mt, entry_str = pandoc.mediabag.fetch(url)
    else
        print("Found DOI: " .. doi)
    end
    return entry_str
end

-- Extract designated filepaths from 1 or 2 dimensional metadata
function get_paths_from(metadata)
    local filepaths = {};
    if metadata then
        if metadata[1].text then
            filepaths[metadata[1].text] = true
        elseif type(metadata) == "table" then
            for _, datum in pairs(metadata) do
                if datum[1] then
                    if datum[1].text then
                        filepaths[datum[1].text] = true
                    end
                end
            end
        end
    end
    return filepaths
end

-- Extract filename and dirname from a given a path
function split_path(filepath)
    local delim = nil
    local len = filepath:len()
    local reversed = filepath:reverse()
    if filepath:find("/") then
        delim = "/"
    elseif filepath:find([[\]]) then
        delim = [[\]]
    else
        return { filename = filepath, dirname = nil }
    end
    local pos = reversed:find(delim)
    local dirname = filepath:sub(1, len - pos)
    local filename = reversed:sub(1, pos - 1):reverse()
    return { filename = filename, dirname = dirname }
end

-- Find bibname in a given filepath list and return the filepath if found
function find_filepath(filename, filepaths)
    for path, _ in pairs(filepaths) do
        local filename = split_path(path)["filename"]
        if filename == bibname then
            return path
        end
    end
    return nil
end

-- Make some TeX descriptions processable by citeproc
function tex2raw(string)
    local symbols = {};
    symbols["{\textendash}"] = "–"
    symbols["{\textemdash}"] = "—"
    symbols["{\textquoteright}"] = "’"
    symbols["{\textquoteleft}"] = "‘"
    for tex, raw in pairs(symbols) do
        local string = string:gsub(tex, raw)
    end
    return string
end

-- get bibtex entry key from bibtex entry string
function get_entrykey(entry_string)
    local key = entry_string:match('@%w+{(.-),') or ''
    return key
end

-- get bibtex entry doi from bibtex entry string
function get_entrydoi(entry_string)
    -- Standard format: doi = {value}
    local doi = entry_string:match('[Dd][Oo][Ii]%s*=%s*["{]*(.-)["}],?')

    -- Alternative format: DOI field contains doi.org/value
    if not doi or doi == "" then
        local doi_field = entry_string:match('[Dd][Oo][Ii][^,}]+')
        if doi_field then
            doi = doi_field:match('doi%.org/([^}]+)')
        end
    end

    -- Ensure we return a lowercase string, not nil
    return (doi and doi:lower()) or ""
end

-- Replace entry key of "entry_string" to newkey
function replace_entrykey(entry_string, newkey)
    entry_string = entry_string:gsub('(@%w+{).-(,)', '%1' .. newkey .. '%2')
    return entry_string
end

-- Make hashmap which key = DOI, value = bibtex entry string
function get_doi_entry_map(bibtex_string)
    local entries = {};
    print("doi2cite: Starting to parse entries")
    local entry_count = 0

    -- Sample the first few hundred chars
    print("doi2cite: BibTeX sample: " .. bibtex_string:sub(1, 200))

    -- More flexible pattern that works with single-line and multi-line entries
    for entry_str in bibtex_string:gmatch('@[^@]+') do
        entry_count = entry_count + 1

        if entry_str:match('}%s*$') then -- Ensure it's a complete entry
            -- Extract entry key for debugging
            local key = entry_str:match('@%w+{(.-),') or 'NO_KEY'


            -- Show DOI field for debugging
            local doi_field = entry_str:match('[Dd][Oo][Ii][^,]+') or 'NO_DOI_FIELD'

            local doi = get_entrydoi(entry_str)
            if doi ~= "" then
                entries[doi] = entry_str
                -- print("doi2cite: Found cached entry for DOI: " .. doi)
            else
                print("doi2cite: No DOI extracted for entry: " .. key)
            end
        else
            print("doi2cite: Incomplete entry detected")
        end
    end

    print("doi2cite: Total entries found: " .. entry_count)
    return entries
end

-- Make hashmap which key = DOI, value = bibtex key string
function get_doi_key_map(bibtex_string)
    local keys = {};
    -- Same flexible pattern here
    for entry_str in bibtex_string:gmatch('@[^@]+') do
        if entry_str:match('}%s*$') then -- Ensure it's a complete entry
            local doi = get_entrydoi(entry_str)
            local key = get_entrykey(entry_str)
            if doi ~= "" then
                keys[doi] = key
            end
        end
    end
    return keys
end

-- function to make directories and files
function make_new_file(filepath)
    if filepath then
        print("doi2cite: creating " .. filepath)
        local dirname = split_path(filepath)["dirname"]
        if dirname then
            os.execute("mkdir -p " .. dirname)
        end
        f = io.open(filepath, "w")
        if f then
            f:close()
        else
            error("Unable to make bibtex file: " .. bibpath .. ".\n"
                .. "This error may come from the missing directory. \n"
            )
        end
    end
end

-- Verify that the given filepath is correct.
-- Catch common Pandoc user mistakes about Windows-formatted filepath.
function verify_path(bibpath)
    if bibpath == nil then
        print("[WARNING] doi2cite: "
            .. "The given file path is incorrect or empty. "
            .. "In Windows-formatted filepath, Pandoc recognizes "
            .. "double backslash (" .. [[\\]] .. ") as the delimiters."
        )
        return "__from_DOI.bib"
    else
        return bibpath
    end
end

--------------------------------------------------------------------------------
-- The main function --
--------------------------------------------------------------------------------
return {
    { Meta = Meta },
    { Cite = Cite }
}
