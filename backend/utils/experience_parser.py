"""
Enhanced Experience Parser

Accurately extracts years of experience from various text patterns:
- "4 years of experience"
- "4+ years"
- "3 yrs"
- "Worked from 2020-2024"
- "Jan 2020 - Present"
- Multiple date ranges (sum them up)
"""

import re
from typing import List, Tuple, Optional
from datetime import datetime


# Patterns for direct "X years" statements
EXPERIENCE_YEARS_PATTERNS = [
    # "4 years of experience", "5+ years", "3 yrs"
    re.compile(r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|work|exp)', re.IGNORECASE),
    # "4+ years in cloud"
    re.compile(r'(\d+)\+?\s*(?:years?|yrs?)\s+(?:in|with|using)', re.IGNORECASE),
    # "Experience: 5 years"
    re.compile(r'experience\s*:?\s*(\d+)\+?\s*(?:years?|yrs?)', re.IGNORECASE),
    # "5 Year Experience"
    re.compile(r'(\d+)\s*(?:year|yr)\s+experience', re.IGNORECASE),
]


# Date range patterns
DATE_RANGE_PATTERNS = [
    # "Jan 2020 - Dec 2023", "January 2020 – Present"
    re.compile(
        r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})'
        r'\s*[-–—to]+\s*'
        r'(?:(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{4})|(present|current|now))',
        re.IGNORECASE
    ),
    # "2020 - 2024", "2020 – Present"
    re.compile(
        r'(\d{4})\s*[-–—to]+\s*(?:(\d{4})|(present|current|now))',
        re.IGNORECASE
    ),
    # "2020-2024" (no spaces)
    re.compile(r'(\d{4})-(\d{4})'),
]


MONTH_MAP = {
    'jan': 1, 'january': 1,
    'feb': 2, 'february': 2,
    'mar': 3, 'march': 3,
    'apr': 4, 'april': 4,
    'may': 5,
    'jun': 6, 'june': 6,
    'jul': 7, 'july': 7,
    'aug': 8, 'august': 8,
    'sep': 9, 'sept': 9, 'september': 9,
    'oct': 10, 'october': 10,
    'nov': 11, 'november': 11,
    'dec': 12, 'december': 12,
}


def parse_experience_years(text: str) -> float:
    """
    Extract years of experience from resume text.

    Strategy:
    1. Look for direct "X years" statements
    2. If not found, parse all date ranges and sum them up
    3. Return the higher of the two (more conservative)

    Args:
        text: Resume text

    Returns:
        Years of experience as float (e.g., 4.5)
    """
    if not text:
        return 0.0

    # Strategy 1: Direct "X years" statements
    direct_years = _extract_direct_years(text)

    # Strategy 2: Date range calculation
    date_range_years = _extract_from_date_ranges(text)

    # Use the more conservative (higher) value
    # Direct statements are usually more accurate for total experience
    # Date ranges might be incomplete (missing early jobs)
    result = max(direct_years, date_range_years)

    # Sanity check: cap at 50 years
    return min(result, 50.0)


def _extract_direct_years(text: str) -> float:
    """Extract years from direct statements like '5 years of experience'."""
    max_years = 0.0

    for pattern in EXPERIENCE_YEARS_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            try:
                # Handle tuple or single match
                years_str = match[0] if isinstance(match, tuple) else match
                years = float(years_str)
                max_years = max(max_years, years)
            except (ValueError, IndexError):
                continue

    return max_years


def _extract_from_date_ranges(text: str) -> float:
    """
    Extract years from date ranges (e.g., 'Jan 2020 - Present').
    Sums up all non-overlapping ranges found.
    """
    ranges: List[Tuple[int, int, int, int]] = []  # (start_year, start_month, end_year, end_month)

    current_year = datetime.now().year
    current_month = datetime.now().month

    # Pattern 1: Month Year - Month Year / Present
    pattern1 = DATE_RANGE_PATTERNS[0]
    for match in pattern1.finditer(text):
        start_month_str = match.group(1).lower()
        start_year = int(match.group(2))

        # End could be another date or "present"
        if match.group(5):  # Present/Current/Now
            end_year = current_year
            end_month = current_month
        else:
            end_month_str = match.group(3).lower() if match.group(3) else 'dec'
            end_year = int(match.group(4)) if match.group(4) else current_year
            end_month = MONTH_MAP.get(end_month_str, 12)

        start_month = MONTH_MAP.get(start_month_str, 1)
        ranges.append((start_year, start_month, end_year, end_month))

    # Pattern 2: Year - Year / Present (no month)
    pattern2 = DATE_RANGE_PATTERNS[1]
    for match in pattern2.finditer(text):
        start_year = int(match.group(1))

        if match.group(3):  # Present/Current/Now
            end_year = current_year
            end_month = current_month
        else:
            end_year = int(match.group(2))
            end_month = 12

        ranges.append((start_year, 1, end_year, end_month))

    # Pattern 3: YYYY-YYYY (compact format)
    pattern3 = DATE_RANGE_PATTERNS[2]
    for match in pattern3.finditer(text):
        start_year = int(match.group(1))
        end_year = int(match.group(2))
        ranges.append((start_year, 1, end_year, 12))

    if not ranges:
        return 0.0

    # Calculate total months from all ranges
    total_months = 0
    for start_year, start_month, end_year, end_month in ranges:
        # Validate range
        if start_year > end_year or (start_year == end_year and start_month > end_month):
            continue  # Invalid range, skip

        if start_year < 1970 or end_year > current_year + 1:
            continue  # Sanity check

        months = (end_year - start_year) * 12 + (end_month - start_month)
        total_months += max(0, months)

    return round(total_months / 12.0, 1)


def extract_companies(text: str) -> List[str]:
    """
    Extract company names from experience section.
    Uses pattern matching for common formats:
    - "Company Name, Location"
    - "Senior Engineer at Company Name"
    - Lines in all caps (company names often capitalized)
    """
    companies = []

    # Pattern: "at CompanyName" or "@ CompanyName"
    at_pattern = re.compile(r'(?:at|@)\s+([A-Z][A-Za-z0-9\s&.,]+(?:Inc|LLC|Ltd|Corp|Corporation)?)', re.MULTILINE)
    for match in at_pattern.finditer(text):
        company = match.group(1).strip()
        if 2 < len(company) < 50:
            companies.append(company)

    # Pattern: Lines that look like company headers (all caps, short)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        # Check if line is mostly uppercase and reasonable length
        if line and len(line) < 60 and sum(1 for c in line if c.isupper()) / len(line) > 0.6:
            # Exclude common section headers
            if not any(h in line.lower() for h in ['experience', 'education', 'skills', 'project']):
                companies.append(line)

    # Deduplicate while preserving order
    seen = set()
    unique_companies = []
    for c in companies:
        c_lower = c.lower()
        if c_lower not in seen and len(c) > 2:
            seen.add(c_lower)
            unique_companies.append(c)

    return unique_companies[:10]  # Cap at 10


def extract_job_titles(text: str) -> List[str]:
    """
    Extract job titles from experience section.
    Looks for common title patterns.
    """
    titles = []

    # Common title keywords
    title_keywords = [
        'engineer', 'developer', 'architect', 'manager', 'lead', 'senior',
        'junior', 'associate', 'analyst', 'consultant', 'specialist',
        'director', 'vp', 'head', 'chief', 'officer', 'designer',
        'scientist', 'researcher', 'technician', 'administrator',
        'coordinator', 'supervisor', 'intern', 'trainee'
    ]

    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line or len(line) > 100:
            continue

        line_lower = line.lower()
        # Check if line contains title keywords
        if any(kw in line_lower for kw in title_keywords):
            # Clean up (remove bullets, dates, locations)
            cleaned = re.sub(r'^[•\-\*\d]+\s*', '', line)
            cleaned = re.sub(r'\d{4}', '', cleaned)  # Remove years
            cleaned = re.sub(r',.*$', '', cleaned)  # Remove everything after comma
            cleaned = cleaned.strip()

            if 5 < len(cleaned) < 80:
                titles.append(cleaned)

    # Deduplicate
    seen = set()
    unique_titles = []
    for t in titles:
        t_lower = t.lower()
        if t_lower not in seen:
            seen.add(t_lower)
            unique_titles.append(t)

    return unique_titles[:8]


# Backward compatibility wrapper for existing code
def estimate_experience_years(text: str) -> float:
    """Alias for parse_experience_years() for backward compatibility."""
    return parse_experience_years(text)
