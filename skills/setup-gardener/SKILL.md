---
name: setup-gardener
description: >
  Periodic maintenance of the agent plugin itself: digests the
  lesson inbox, prunes skills, and proposes improvements. Use when the
  user says "gardener", "tend the setup", "digest the lessons",
  "setup maintenance", or when the session reminder
  indicates accumulated lessons.
---

The setup is code too: apply the simplicity ladder
(`ponytail` skill). Edit before adding, delete before editing.
Every change is proposed first and applied only with user approval.
State (lessons) lives in `~/.mle-setup/lessons.md`; the plugin
itself is edited in its git repo.

## 1. Digest the inbox
Read `~/.mle-setup/lessons.md` (if it does not exist, create it with its header
and report an empty inbox). For each lesson, choose ONE destination:
- Adjustment in the injection hook (session-context) if it is a
  cross-cutting always-on rule.
- Edit an existing skill (if it refines something that already exists).
- Rule in a repo AGENTS.md (if it belongs to a single project:
  indicate which one; apply it next time we are there).
- NEW skill only with the rule of three: the same class of lesson
  appeared 3 times. Before that, it is one line, not a skill.
- Case for the knowledge base (kb skill) if the lesson is a
  solved problem more than a behavior rule.
- Discard, with one-line reason (one-off case, already covered,
  contradicts a better rule).

## 2. Prune
- Is injected session-context content too long? Move
  detail to skills or delete it.
- Do skills overlap? Propose a merge.
- Ask the user which skills they did not use or did not find useful since the
  last maintenance: candidates for deletion. A smaller setup that
  gets used is worth more than a complete one that gets in the way.
- Skill that did NOT trigger when it should have? The problem is its
  description (that is the trigger): rewrite it with the phrases the
  user actually says.

## 3. Refresh
- From time to time: review release notes from the upstreams we
  vendor (obra/superpowers and DietrichGebert/ponytail on GitHub)
  and propose bringing in improvements that apply. We are a vendored fork:
  improvements do not arrive on their own.

## 4. Close
- Apply the approved changes.
- Move processed lessons to `~/.mle-setup/lessons-archive.md`
  (with their destination noted) and leave the inbox empty.
- `git add -A && git commit` in the plugin repo with a semantic
  message by topic, and bump the version in plugin.json and
  marketplace.json. The plugin history is the record of what was
  learned.
- Suggested cadence if the user did not define it: every 2 weeks or
  when the inbox exceeds 10 lessons, whichever happens first.
