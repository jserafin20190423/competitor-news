# competitor-news
Weekly search for news releases from competitors
# PEX Competitor Research Agent

An AI-powered research agent that monitors PEX (cross-linked polyethylene) manufacturers Uponor, Georg Fischer, and Viega for important business announcements.

## Features

- **Automated Monitoring**: Scrapes company websites for news and announcements
- **AI Analysis**: Uses OpenAI GPT-4 to analyze importance and business implications
- **Intelligent Filtering**: Filters out low-importance content (ESG, trade shows, routine updates)
- **Scheduled Reports**: Runs every Sunday at 3 AM via GitHub Actions
- **Manual Execution**: Can be triggered manually when needed
- **Historical Tracking**: Only processes new announcements since last run

## Setup Instructions

### 1. Fork/Clone Repository
```bash
git clone <your-repo-url>
cd pex-competitor-agent
```

### 2. Set up OpenAI API Key
1. Go to your GitHub repository settings
2. Navigate to "Secrets and variables" → "Actions"
3. Add a new repository secret:
   - Name: `OPENAI_API_KEY`
   - Value: Your OpenAI API key

### 3. Enable GitHub Actions
1. Go to the "Actions" tab in your repository
2. Enable workflows if prompted
3. The workflow will automatically run every Sunday at 3 AM UTC

### 4. Manual Execution
To run the agent manually:
1. Go to "Actions" tab
2. Select "PEX Competitor Research Agent"
3. Click "Run workflow"

## How It Works

1. **Data Collection**: Scrapes websites for news and press releases
2. **Content Analysis**: Uses OpenAI to analyze each announcement for:
   - Importance score (0.0-1.0)
   - Business category
   - Summary of key points
   - Business implications
3. **Filtering**: Excludes low-importance content based on AI analysis
4. **Report Generation**: Creates markdown reports saved to `/reports/` folder
5. **Timestamp Tracking**: Records last run time to avoid duplicate processing

## Companies Monitored

- **Uponor**: uponor.com
- **Georg Fischer**: georgfischer.com (Uponor's parent company)
- **Viega**: viega.com

## Report Format

Reports include:
- Executive summary
- Separate sections for each company
- For each announcement:
  - Title and date
  - Importance score
  - Category (Product Launch, Financial Results, etc.)
  - AI-generated summary
  - Business implications analysis
  - Source link

## File Structure

```
├── main.py                 # Main agent script
├── requirements.txt        # Python dependencies
├── .github/workflows/      # GitHub Actions workflow
├── reports/               # Generated reports (auto-created)
├── last_run_timestamp.txt # Tracks last execution (auto-created)
└── README.md              # This file
```

## Customization

To modify the agent:

1. **Add/Remove Companies**: Edit the `companies` dictionary in `main.py`
2. **Change Schedule**: Modify the cron expression in `.github/workflows/research.yml`
3. **Adjust Filtering**: Modify the OpenAI prompt in the `analyze_with_openai` method
4. **Report Format**: Update the `generate_report` method

## Troubleshooting

- **No reports generated**: Check GitHub Actions logs for errors
- **API errors**: Verify your OpenAI API key is correctly set
- **Scraping issues**: Some websites may block automated access; check logs for specific errors

## Limitations

- LinkedIn scraping is not implemented due to anti-bot measures
- Website structure changes may require scraper updates
- Rate limited to avoid overwhelming target websites
- Dependent on OpenAI API availability and costs

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is for educational and business intelligence purposes. Ensure compliance with target websites' terms of service and robots.txt files.
