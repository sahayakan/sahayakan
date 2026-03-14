# Meeting Summary Agent

The Meeting Summary agent processes meeting transcripts to extract action items, decisions, and key discussion topics.

## Input

| Parameter | Type | Description |
|-----------|------|-------------|
| `transcript_id` | string | Identifier for the transcript in the knowledge cache |

## What It Does

1. Loads the meeting transcript from the knowledge cache
2. Gathers context: participants, related projects, previous meeting summaries
3. Analyzes the transcript with the LLM
4. Produces a structured meeting summary

## Output

| Field | Description |
|-------|-------------|
| `action_items` | List of action items with assignees and deadlines |
| `decisions` | Key decisions made during the meeting |
| `key_topics` | Main discussion topics and summaries |
| `participants` | List of participants and their contributions |
| `follow_ups` | Items requiring follow-up |

## Preparing Transcripts

Place meeting transcripts in the knowledge cache before running the agent:

```
knowledge-cache/meetings/transcripts/{transcript_id}.txt
```

Supported formats:

- Plain text transcripts
- Timestamped transcripts (speaker labels help improve accuracy)

## Running

```bash
python3 -m cli.main run meeting-summary --transcript meeting-2024-01-15

python3 -m cli.main report view meeting_summaries meeting-2024-01-15
```

## Report Location

```
knowledge-cache/agent_outputs/meeting_summaries/{transcript_id}.json
knowledge-cache/agent_outputs/meeting_summaries/{transcript_id}.md
```
