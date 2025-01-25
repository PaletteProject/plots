# Palette Plots

A visualization tool to provide burndown charts for the Palette Project team.

It will eventually be expanded to provide visualizations for instructors using the tool.

## Using the Script

- Ensure you have valid GitHub personal access token
- Create or update local .env file with:

```.dotenv
    GITHUB_TOKEN=your_token
    ORG=PaletteProject
    PROJECT_TITLE="Palette"
    
    YEAR_START=2025
    MONTH_START=1
    DAY_START=12

    YEAR_END=2025
    MONTH_END=1
    DAY_END=25
    
```

Adjust dates to align with project snapshot periods.