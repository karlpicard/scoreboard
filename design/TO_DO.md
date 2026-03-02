# Design To‑Do

# This file tracks upcoming features and enhancements for the scoreboard app.
# Phase 1
- [ ] Add a central dashboard/page that lists all active games with quick access links (dashboard should be site entry page)
- [ ] Dashboard should include a "Go to game" option for each listed game
- [ ] Add a "New Game" button to the dashboard to create games directly (visible to write-enabled users only)
- [ ] Track score changes for each game so history can be viewed
- [ ] Display the score at the bottom of the game detail, do not show this on the dashboard
- [ ] Implement read-only mode for viewer links (no controls)
- [ ] Add logic/permissions so only certain users can update scores
- [ ] Dependency setup in a new environment
- [ ] Update the font on the site, system like font, Change the color for the different teams
- [ ] Deploy to production (Docker/Heroku), ensure there are DB backups, have a user friendly URL
# Phase 2 - Testing
- [ ] Add tests for API endpoints and core functions (use pytest or similar)
- [ ] Create test scripts to exercise server functionality automatically
- [ ] Improve error handling and user feedback
# Phase 3 - User enhancement
- [ ] Mobile-friendly layout improvements
- [ ] Create Bx and Gx options
- [ ] Create date range for the game dashboard
- [ ] Add game deletion/archival endpoint
- [ ] add a time element
# Phase 4 - Future items
- [ ] Add authentication for private games
- [ ] Export game data or logs as CSV
- [ ] Create different Team dashboard for different groups
- [ ] Support custom scoring rules or timers