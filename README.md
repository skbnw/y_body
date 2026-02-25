# y_body

Yahoo News Scraper Repository.

## CSS Selector Note (as of 2026-02-25)

Yahoo! News has recently updated its HTML structure, changing many functional classes (hashes) to Styled-Components classes.
The scraper now uses the following stable classes:

- **Article Link**: `sc-1gg21n8-0` (formerly hash-based like `cDTGMJ`)
- **Content Wrapper**: `sc-278a0v-0` (formerly `iiJVBF`)
- **Title**: `sc-3ls169-0` (formerly `dHAJpi`)
- **Time info**: `sc-16vsoxb-1` (formerly `faCsgc`)
- **Article Body**: `article_body` (remains standard)

These `sc-*` classes appear more consistent across different media outlets and page versions as of late February 2026.
If scraping fails with "Found 0 articles", please verify if these classes have been updated again.
