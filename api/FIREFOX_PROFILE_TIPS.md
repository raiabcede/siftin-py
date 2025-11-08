# Firefox Profile Tips - Preventing Logout Issues

## Why You Keep Getting Logged Out

When using Selenium with Firefox profiles, you might get logged out due to:

1. **Profile Lock**: If Firefox is already running with that profile, Selenium can't use it
2. **Profile Copying**: Selenium may create a temporary copy that doesn't have your session
3. **Automation Detection**: LinkedIn may detect automation and log you out
4. **Session Expiry**: Cookies might expire between runs

## Solutions

### 1. Close Firefox Before Running
**IMPORTANT**: Always close all Firefox windows before running the scraper.

```bash
# Windows
taskkill /im firefox.exe /f

# Linux/Mac
killall firefox
```

### 2. Use a Dedicated Profile
Create a separate Firefox profile just for automation:

1. Open Firefox
2. Type `about:profiles` in address bar
3. Click "Create a New Profile"
4. Name it "selenium" or "automation"
5. Log into LinkedIn in this profile
6. Close Firefox
7. Use this profile path in your `.env` file

### 3. Check Your Profile Path
Make sure you're using the correct profile path:

- **Windows**: `C:\Users\YourName\AppData\Roaming\Mozilla\Firefox\Profiles\xxxxx.default-release`
- **Linux**: `~/.mozilla/firefox/xxxxx.default-release`
- **Mac**: `~/Library/Application Support/Firefox/Profiles/xxxxx.default-release`

To find your profile:
1. Open Firefox
2. Type `about:profiles` in address bar
3. Find your profile
4. Click "Open Folder" next to "Root Directory"
5. Copy the full path

### 4. Verify Login Before Running
Check if you're logged in:

```bash
# Check auth status via API
curl http://localhost:8000/api/linkedin-auth-status
```

### 5. Don't Run Multiple Instances
Only run one scraper instance at a time. Multiple instances can conflict.

## Best Practices

1. ✅ Close Firefox completely before running
2. ✅ Use a dedicated profile for automation
3. ✅ Verify login status before scraping
4. ✅ Don't manually use Firefox while scraper is running
5. ✅ Keep your LinkedIn session active (don't let it expire)

## Troubleshooting

### Still Getting Logged Out?

1. **Check if Firefox is running**:
   ```bash
   # Windows
   tasklist | findstr firefox
   
   # Linux/Mac
   ps aux | grep firefox
   ```

2. **Verify profile path is correct**:
   - Make sure the path exists
   - Make sure it's a directory, not a file
   - Make sure you have read/write permissions

3. **Check LinkedIn cookies**:
   - Open Firefox manually
   - Go to LinkedIn
   - Check if you're logged in
   - If not, log in again
   - Close Firefox completely
   - Try running scraper again

4. **Try a fresh profile**:
   - Create a new Firefox profile
   - Log into LinkedIn
   - Use that profile path

## Environment Variable

Make sure your `.env` file has:

```
FIREFOX_PROFILE_PATH=C:\Users\YourName\AppData\Roaming\Mozilla\Firefox\Profiles\xxxxx.default-release
```

Or on Linux/Mac:

```
FIREFOX_PROFILE_PATH=/home/username/.mozilla/firefox/xxxxx.default-release
```

