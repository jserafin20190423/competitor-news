#!/usr/bin/env python3
"""
PEX Competitor Research Agent
Monitors Uponor, Georg Fischer, and Viega for important announcements
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import requests
from bs4 import BeautifulSoup
import openai
from dataclasses import dataclass, asdict
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class Announcement:
    """Data structure for announcements"""
    company: str
    title: str
    date: str
    url: str
    content: str
    source: str
    importance_score: float
    category: str
    summary: str
    implications: str

class CompetitorAgent:
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.companies = {
            'uponor': {
                'name': 'Uponor',
                'websites': ['https://www.uponor.com', 'https://www.georgfischer.com'],
                'linkedin': 'https://www.linkedin.com/company/uponor'
            },
            'viega': {
                'name': 'Viega', 
                'websites': ['https://www.viega.com'],
                'linkedin': 'https://www.linkedin.com/company/viega'
            }
        }
        self.timestamp_file = 'last_run_timestamp.txt'
        self.reports_dir = 'reports'
        
        # Create reports directory if it doesn't exist
        os.makedirs(self.reports_dir, exist_ok=True)

    def get_last_run_timestamp(self) -> datetime:
        """Get the timestamp of the last run, with max 30-day lookback"""
        try:
            max_lookback = datetime.now() - timedelta(days=30)
            
            if os.path.exists(self.timestamp_file):
                with open(self.timestamp_file, 'r') as f:
                    timestamp_str = f.read().strip()
                    last_run = datetime.fromisoformat(timestamp_str)
                    
                    # Ensure we don't look back more than 30 days
                    if last_run < max_lookback:
                        logger.info(f"Last run was {last_run}, but limiting lookback to 30 days: {max_lookback}")
                        return max_lookback
                    else:
                        return last_run
            else:
                # If no timestamp file, look back 7 days (safe default)
                default_lookback = datetime.now() - timedelta(days=7)
                logger.info(f"No timestamp file found, using default 7-day lookback: {default_lookback}")
                return default_lookback
                
        except Exception as e:
            logger.error(f"Error reading timestamp: {e}")
            # Fall back to 7 days on error
            return datetime.now() - timedelta(days=7)

    def update_timestamp(self):
        """Update the timestamp file with current time"""
        try:
            with open(self.timestamp_file, 'w') as f:
                f.write(datetime.now().isoformat())
        except Exception as e:
            logger.error(f"Error updating timestamp: {e}")

    def scrape_website_news(self, url: str, company: str, since_date: datetime) -> List[Dict]:
        """Scrape news/announcements from company websites"""
        announcements = []
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            # Common news/press release URL patterns
            news_paths = ['/news', '/press', '/press-releases', '/media', '/newsroom', '/media-center']
            
            for path in news_paths:
                try:
                    news_url = url + path
                    response = requests.get(news_url, headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        
                        # Look for common news article patterns
                        article_selectors = [
                            'article', '.news-item', '.press-release', 
                            '.media-item', '[class*="news"]', '[class*="press"]'
                        ]
                        
                        for selector in article_selectors:
                            articles = soup.select(selector)
                            
                            for article in articles:
                                try:
                                    # Extract title
                                    title_elem = article.find(['h1', 'h2', 'h3', 'h4', 'a'])
                                    if not title_elem:
                                        continue
                                    
                                    title = title_elem.get_text().strip()
                                    
                                    # Extract link
                                    link_elem = article.find('a')
                                    if link_elem and link_elem.get('href'):
                                        article_url = link_elem.get('href')
                                        if article_url.startswith('/'):
                                            article_url = url + article_url
                                    else:
                                        article_url = news_url
                                    
                                    # Extract date (this is tricky and site-specific)
                                    date_elem = article.find(['time', '[class*="date"]', '[datetime]'])
                                    article_date = datetime.now()  # Default to now if no date found
                                    
                                    if date_elem:
                                        date_str = date_elem.get('datetime') or date_elem.get_text()
                                        # Try to parse date (simplified - would need more robust parsing)
                                        try:
                                            article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                                        except:
                                            pass
                                    
                                    # Only include if after since_date
                                    if article_date >= since_date:
                                        announcements.append({
                                            'company': company,
                                            'title': title,
                                            'date': article_date.isoformat(),
                                            'url': article_url,
                                            'content': article.get_text()[:1000],  # First 1000 chars
                                            'source': 'website'
                                        })
                                        
                                except Exception as e:
                                    logger.warning(f"Error processing article: {e}")
                                    continue
                            
                            if articles:  # If we found articles with this selector, break
                                break
                        
                        if announcements:  # If we found announcements, break
                            break
                            
                except requests.RequestException as e:
                    logger.warning(f"Error accessing {news_url}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            
        return announcements

    def analyze_with_openai(self, announcement: Dict) -> Announcement:
        """Use OpenAI to analyze announcement importance and generate insights"""
        
        prompt = f"""
        You are analyzing a business announcement from {announcement['company']}, a PEX (cross-linked polyethylene) piping manufacturer.

        Title: {announcement['title']}
        Content: {announcement['content']}
        Date: {announcement['date']}
        Source: {announcement['source']}

        Please analyze this announcement and provide:

        1. IMPORTANCE SCORE (0.0-1.0): Rate how important this is for understanding the company's competitive position
           - 0.0-0.3: Low importance (routine updates, minor personnel, ESG initiatives)
           - 0.4-0.6: Medium importance (product updates, regional partnerships)
           - 0.7-1.0: High importance (major product launches, strategic partnerships, financial results, C-suite changes)

        2. CATEGORY: Classify as one of: Product Launch, Financial Results, Partnership, Personnel, Project Win, Technology, Regulatory, Other

        3. SUMMARY: Provide a 2-3 sentence summary of the key points

        4. BUSINESS IMPLICATIONS: Analyze what this means for their competitive position, market strategy, or business prospects (2-3 sentences)

        Filter OUT announcements that are primarily about:
        - ESG/sustainability initiatives without business impact
        - Community involvement or charitable activities
        - Trade show booth announcements
        - Routine compliance updates
        - Minor personnel changes (non-C-suite)

        Respond in this exact JSON format:
        {
            "importance_score": 0.0,
            "category": "Category",
            "summary": "Summary text",
            "implications": "Business implications text",
            "should_include": true
        }
        """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            result = json.loads(response.choices[0].message.content)
            
            # Only include if should_include is True and importance_score > 0.3
            if result.get('should_include', False) and result.get('importance_score', 0) > 0.3:
                return Announcement(
                    company=announcement['company'],
                    title=announcement['title'],
                    date=announcement['date'],
                    url=announcement['url'],
                    content=announcement['content'],
                    source=announcement['source'],
                    importance_score=result['importance_score'],
                    category=result['category'],
                    summary=result['summary'],
                    implications=result['implications']
                )
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error analyzing announcement with OpenAI: {e}")
            return None

    def collect_announcements(self, since_date: datetime) -> List[Announcement]:
        """Collect all announcements from all sources"""
        all_announcements = []
        
        for company_key, company_info in self.companies.items():
            logger.info(f"Collecting announcements for {company_info['name']}")
            
            # Scrape websites
            for website in company_info['websites']:
                logger.info(f"Scraping {website}")
                raw_announcements = self.scrape_website_news(website, company_info['name'], since_date)
                
                # Analyze each announcement with OpenAI
                for raw_announcement in raw_announcements:
                    analyzed = self.analyze_with_openai(raw_announcement)
                    if analyzed:
                        all_announcements.append(analyzed)
                        
                # Rate limiting
                time.sleep(2)
            
            # Note: LinkedIn scraping would require different approach due to anti-bot measures
            # For now, we'll focus on website scraping
            
        return all_announcements

    def generate_report(self, announcements: List[Announcement]) -> str:
        """Generate the final report"""
        
        if not announcements:
            return """# PEX Competitor Research Report
            
## Summary
No significant announcements found since the last report.

## Companies Monitored
- Uponor (including Georg Fischer)
- Viega

Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

        # Sort by company, then by date
        announcements.sort(key=lambda x: (x.company, x.date), reverse=True)
        
        report = f"""# PEX Competitor Research Report

Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary
Found {len(announcements)} significant announcements from PEX manufacturers.

"""

        # Group by company
        companies = {}
        for announcement in announcements:
            if announcement.company not in companies:
                companies[announcement.company] = []
            companies[announcement.company].append(announcement)

        # Generate sections for each company
        for company, company_announcements in companies.items():
            report += f"\n## {company}\n\n"
            
            for announcement in company_announcements:
                report += f"### {announcement.title}\n"
                report += f"**Date:** {announcement.date}\n"
                report += f"**Category:** {announcement.category}\n"
                report += f"**Importance Score:** {announcement.importance_score:.1f}/1.0\n"
                report += f"**Source:** {announcement.source}\n\n"
                report += f"**Summary:** {announcement.summary}\n\n"
                report += f"**Business Implications:** {announcement.implications}\n\n"
                report += f"**Source Link:** {announcement.url}\n\n"
                report += "---\n\n"

        return report

    def save_report(self, report: str):
        """Save the report to a file"""
        timestamp = datetime.now().strftime('%Y-%m-%d')
        filename = f"{self.reports_dir}/competitor_report_{timestamp}.md"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            logger.info(f"Report saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving report: {e}")

    def run(self):
        """Main execution method"""
        logger.info("Starting PEX Competitor Research Agent")
        
        try:
            # Get last run timestamp
            since_date = self.get_last_run_timestamp()
            logger.info(f"Looking for announcements since: {since_date}")
            
            # Collect announcements
            announcements = self.collect_announcements(since_date)
            logger.info(f"Found {len(announcements)} relevant announcements")
            
            # Generate report
            report = self.generate_report(announcements)
            
            # Save report
            self.save_report(report)
            
            # Update timestamp
            self.update_timestamp()
            
            logger.info("Research agent completed successfully")
            
        except Exception as e:
            logger.error(f"Error in main execution: {e}")
            raise

if __name__ == "__main__":
    agent = CompetitorAgent()
    agent.run()
