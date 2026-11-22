# LiveAsk landing page copy

Voice: product as the hero (copy-registers.md 11), one move from technical-dry (2): the mechanism in verb-led steps
Pairs: exact, plain; sure, not loud; dry only in empty states and errors
Person: the product is the subject (LiveAsk, the console, the screen); "you" for the presenter; "we" once, in the FAQ's admission
Sentences: mostly 8 to 16 words; one longer where it explains
Humour: none on the page; a dry line only in the empty states
House words: room, code, question, poll, console, screen (the same word every time)
Never: virtue words, a pun on the name, a strip of figures, invented customers or numbers

Every fact below is in PROJECT_REQUIREMENTS.md, API_SPECIFICATION.md or the shipped app. No price, no customer, no quote: the brief has none, so the page has none.

## Nav

Questions
Polls
Screen
FAQ
Create a room

## Hero

No sign-up needed. Rooms expire after 24 hours.

Live Q&A and polls for presenters

Show a QR code. Your audience asks questions, upvotes the best ones and votes in polls from their phones, and the projector updates as they do.

Create a room
Join a room

## Console

Run the room from one page

Hide a question, mark one answered, open a poll or close the room. Phones and the projector follow every change.

See the projector view

## Questions

Questions rise by votes

The most upvoted question moves to the top, and ties go to the newest. A phone gets one vote per question.

Ask in 280 characters
Add a name or stay anonymous. A phone can post five questions a minute.

Upvote a question once
A second tap takes the vote back.

Hide a question
It leaves every phone and the projector at once. You still see it in the console.

## Polls

Polls with live results

Write a question and two to six options, then open the poll. The bars move as phones vote.

People can change their vote until you close the poll.

Options: 2 to 6
Votes per phone: 1, changeable
Results shown on: phones, host, screen

## Screen

A screen for the projector

Open the screen link on the projector. It shows the room code, a QR code, the top six questions and the poll in progress.

Try the screen view

Room code: six characters, set large.
QR code: opens the audience page.
Top questions: the six most upvoted open ones.
Live poll: the newest open poll.

## Sync

Every server hears every change

LiveAsk saves each question in PostgreSQL and announces it to all servers, so a phone on one server sees a question sent through another.

## FAQ

Answers to common questions

What a room keeps, how long it lasts and what the limits are.

See the presenter's page

Do people need an account?
No. Phones join with the link or the 6-character code. A name is optional, and LiveAsk asks for no other personal details.

How long does a room last?
A room expires 24 hours after you create it.

What if I lose the host link?
LiveAsk shows it once and keeps only a hash of it, so we cannot show it again. Your browser remembers it on the device that created the room; save the link before you close the page.

How many questions can one person ask?
Five a minute from each phone, so one person cannot fill the list.

Can people see hidden questions?
No. A hidden question leaves every phone and the projector. You can bring it back from the console.

Made for
Class presentations
Club meetings
Small events
Lectures
Workshops
Meetups

## Close

Create your first room

A room needs a title and one click. The projector view shows its QR code straight away.

Create a room

## Footer

LiveAsk 2026
Questions
Polls
Screen
FAQ
Join a room
Source code

## Microcopy for the app views

Audience, no questions yet: No questions yet. Ask the first one.
Host, no questions yet: No questions yet. They appear here as phones send them.
Screen, no questions yet: Scan the QR code and ask the first question.
Too many questions: Five questions a minute is the limit. Try again in a moment.
Room closed: This room is closed. Questions and votes are off.
Room not found: No room has this code. Check the 6 characters on the screen.
Join code error: Write the 6 characters shown on the projector.
Create error, empty title: Write a title for the room, up to 120 characters.
Network error: No connection. LiveAsk retries on its own.
