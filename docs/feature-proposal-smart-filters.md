# Feature Proposal: Smart Filters & Personalized Collections

## Overview
Introduce smart filtering and personalized event collections so visitors can quickly discover events that match their interests, time windows, and preferred neighborhoods. The feature combines lightweight user preferences stored locally with curated, context-aware filters on the homepage.

### Goals
- Reduce decision fatigue for new visitors facing an undifferentiated list of events.
- Encourage repeat usage by recognizing and surfacing an individual's preferred themes.
- Provide a framework that can scale into future, richer personalization (e.g., account-based recommendations) without backend changes today.

### Non-Goals
- Building server-side profiles or requiring user authentication.
- Guaranteeing deterministic ordering—client-side personalization remains best-effort.

## User Value
- **Faster discovery:** Visitors can toggle curated filters such as "After Work", "Family Friendly", or "Late Night" to view the most relevant events without manually scanning long lists.
- **Personal relevance:** A simple preference setup (interests, typical availability, favorite venues) saved to local storage tailors the event feed without requiring accounts or backend changes.
- **Retention:** Returning users see content that matches prior selections, encouraging them to rely on Spontis for planning.

## Feature Breakdown
1. **Curated Smart Filters**
   - Add a filter bar with predefined collections (e.g., Time of Day, Mood, Neighborhood).
   - Each collection corresponds to a combination of tags/time ranges computed on the client.
   - Filters stack, enabling combinations like "Indie Music" + "Tonight".
   - Display active chips with clear removal affordances and announce changes via ARIA live regions.

2. **Preference Onboarding Modal**
   - Lightweight modal triggered on first visit or via "Personalize" button.
   - Allows visitors to select interests (music, art, film, workshops), preferred days, and favorite venues.
   - Save selections to `localStorage` so preferences persist per device.

3. **Personalized Feed Highlight**
   - When preferences exist, surface a "For You" section at the top of the event list.
   - This section reorders events client-side, boosting matches while keeping full list accessible below.

4. **Data Support Enhancements**
   - Expand event schema with optional fields: `neighborhood`, `price_level`, `audience` (e.g., 18+, family).
   - Update scraper mappings gradually; fallback to heuristics when data missing.
   - Instrument scraper to record field coverage percentages so we understand freshness and quality.

## User Stories & Acceptance Criteria
- **As a first-time visitor**, I can browse curated collections (Tonight, Budget-Friendly, Live Music) and immediately see matching events without filling out a form.
  - *Acceptance:* Filter chips appear on page load, applying a client-side subset of events and updating counts in <200ms after data load.
- **As a returning visitor**, I can re-open the personalize modal to adjust my interests, and the "For You" section refreshes within the same session.
  - *Acceptance:* Preferences persist in local storage and propagate to the feed without page reload.
- **As an accessibility user**, I can navigate filters via keyboard and hear confirmation when filters toggle.
  - *Acceptance:* Focus order respects DOM order, ARIA announcements fire on add/remove, and controls meet contrast ratio guidelines.

## Data & Instrumentation Requirements
- Extend `events.json` schema with optional metadata while keeping backward compatibility. Unknown fields default to `null` and are omitted from UI chips.
- Add analytics hooks (Plausible custom events) for: filter chip clicks, preference modal open/complete, "For You" section impressions.
- Log anonymized preference selections in local storage solely for personalization; no network transmission in MVP.

## Implementation Notes
- **Progressive rollout:** Ship curated filters first; personalize once schema updates are available.
- **Performance:** Precompute filter buckets when loading events JSON to avoid repeated scans per interaction.
- **Accessibility:** Ensure filter bar is keyboard navigable and uses ARIA attributes for state changes.
- **Offline-safe:** Guard all personalization logic behind feature detection for `localStorage` and degrade gracefully to curated filters only.
- **Testing:** Add unit tests for filter combination logic and Cypress regression for modal interactions.

## Success Metrics
- Increase in average events clicked per session.
- Higher return visits measured via privacy-friendly analytics (e.g., Plausible goals for filter usage).
- Qualitative user feedback indicating easier discovery.

## Open Questions
- Should filters be global across the app or scoped to specific venues pages in the future?
- Do we need lightweight server-side logging to understand preference selections, or is client-only enough?
- What heuristics should drive ranking boosts (e.g., additive scoring vs. weighted categories), and how do we tune them without creating filter bubbles?
- How do we sunset or rotate curated collections so the bar stays fresh without manual intervention every week?

