# T3.4 acceptance walkthrough - is the deal card's collaboration done?

**Purpose:** decide whether [#28 (T3.4: collaboration upgrades)](https://github.com/nosuper/10082026-OS/issues/28) is complete and can be **closed**, or whether fix tickets need filing. Nothing in here is blocking - every question is a judgement automation cannot make. Two answers change what gets built next: who may delete a file, and whether the file manager should also carry job files.

**From:** Claude (the implementing agent) - **To:** the founder, plus Linh for the producer checks, plus the next Claude session - **How your answers will be used:** the next session reads this file, treats every "yes" as a verified acceptance criterion, and files fix tickets for the rest.

## Context

This ticket is your own list from the T3.1+T3.2 walkthrough, built:

- **@mention** the other seat in a comment, with a suggestion popup, and a notification for whoever was named.
- **Edit and delete your own comment** - and only your own.
- **Inline images in comments** - paste a screenshot straight into the box.
- **A file manager** at `/aura/files`: every file across every deal, filtered by deal, type or uploader, renamed or deleted from there.

Recorded and deliberately *not* built (your words, from the same walkthrough): email integration on the deal card, and actual shareable/public file links. The file manager is shaped so sharing lands on top of it rather than needing it unpicked - every row already carries whether the file is private.

What automation covers: the mention payloads, the own-comment-only gate for both seats, the file listing's permission boundary, and a browser run that posts, edits and deletes a comment, picks a name out of the @ popup, and renames a file from the manager. What it cannot see is everything below.

The test site is **http://192.168.1.94:8000/aura/deals** (`anhchung.work@gmail.com` for the founder seat, Linh's `plinhcontact@gmail.com` for the producer seat). **Hard-refresh first (Ctrl+Shift+R)** so you're not on a cached bundle.

## How to answer

15 minutes at a browser, plus 5 minutes of Linh's time - the mention and the "can she edit my comment" checks need two seats. Partial answers and "I don't know" are useful. Answer inline under each `>`.

## Comments

### Open a deal, type `@` in the comment box. Does Linh's name come up, and does picking it put her name in the comment?

_Why this matters: the popup only offers the two operating seats, never yourself. If the list is empty or shows the wrong people, the seat list behind it is wrong._

>

### Post that comment. Does Linh see a notification, and does clicking it land her on the right deal card?

_Why this matters: a mention that notifies nobody is decoration. The notification links to `/aura/deals?deal=…`, which opens the card in the app - not the Desk form, which is where Frappe would have sent her by default._

>

### Write a comment, then edit it. Does the change stick, and does the thread say it was edited?

>

### Delete one of your own comments. Gone for good, no undo - is one confirm tap enough, or do you want a real "are you sure"?

_Why this matters: I used two taps in place of a browser confirm box, because a confirm dialog inside the card dialog is the one thing worse than a mis-tap. If a comment ever disappears by accident, tell me._

>

### Ask Linh to open the same deal. Can she see Edit and Delete on your comment?

_Why this matters: this is the rule the whole ticket turns on. You both have full write on every deal, so nothing but this gate stops either of you rewriting the other's words. She should see the buttons only on her own._

>

### Paste a screenshot straight into the comment box. Does it appear in the box as you type, and is it still there for Linh after you post?

>

### That pasted image is stored as an ordinary attachment on the deal - so it also shows in the card's Attachments list and in the file manager. Right, or should comment images be kept separate?

_Why this matters: I chose "a file is a file" - one place files live, nothing hidden. The alternative is a separate bucket for comment images, which means one more thing to explain and one more place to look._

>

### The comment box is now a proper editor - bold, lists, a slash menu, emoji. Useful, or noise on a box you use for "khách muốn quay trước Tết"?

_Why this matters: the editor came as one piece with mentions and image paste. It can be trimmed back to a plainer box if the extra buttons get in the way._

>

### Opening a deal card now downloads the editor the first time (about a second on a good connection, cached after). Did the card feel slower to open?

_Why this matters: the same editor already ships for the paperwork page, so nothing new was added to the app - but the deal card is the screen you open most, and it now pays for it once per browser._

>

## The file manager

### Click **Files** in the top nav. Are the files you expect there, each showing which deal it came from?

>

### Filter by deal, then by type, then by uploader. Do the filters do what you'd expect, and is the search box on top of them useful or redundant?

>

### Rename a file to something you'd actually recognise. Does the new name stick after a reload?

>

### Delete a file from the manager. It's gone from the deal card too - is that what you expected, or did you expect "remove from this list only"?

>

### Right now **either seat may rename or delete any file on any deal** - the same rule as attaching one. Comments are the opposite (your own only). Is that split right, or should files be own-uploads-only too?

_Why this matters: I read a file as shared material - a badly named brief is everyone's problem - and a comment as authored speech. If you'd rather Linh could not delete a contract you attached, this is the ticket to say so._

>

### The manager lists **deal** files only. Generated paperwork hangs on jobs and does not appear. Missing, or right?

_Why this matters: "all attached files across deals" is what the ticket said, so that is what was built. Adding jobs is small if you want one page for everything._

>

### There is no upload button on the Files page - files arrive through a deal card, because that is where someone knows which deal the file belongs to. Fine, or do you want to upload from here?

>

### Every file is still private: the link only opens for a signed-in seat. The page shows a **public** badge for any file that isn't, so the day sharing exists you can see at a glance which is which. Is that the right way to show it?

>

## Linh's seat

### Can Linh open the Files page, see the same files, rename one and delete one?

>

### Can she paste an image into a comment and @mention you?

>

### On her phone, does the Files table read at all, or is it a horizontal-scroll mess?

_Why this matters: the same question went unanswered for the deals table last time. The table scrolls sideways inside its own box rather than pushing the page around, but that is not the same as being usable._

>

## Anything else?

### Anything you saw during the walkthrough - a slow load, odd wording, a worry about the next tickets - that we didn't ask about?

>
