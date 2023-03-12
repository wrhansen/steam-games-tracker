# Perfect Games

This series of scripts and automation is my attempt at keeping track of all the
perfect games that I have achieved on my Steam Deck. Steam does this on your
profile screen, however I noticed that some games actually release more achievements
and it causes you to lose your "perfect game" count when they do that until you
play the game again and complete the new achievements.

Here's what my current profile looks like on steam:

![steam profile](assets/steam-profile.png)

So there's a few things I want to accomplish here:

* Store "perfect game" data in my second brain
* Keep track of which games that were previously perfect have new achievements

I think I can accomplish all of this by entering the information into my second
brain (Notion) and format a database that shows which games have lost their
"perfect game" rating.

# Implementation

I am going to shoot for doing the following:

* Use Steam Web API to get all games played
* Figure out which games I've played are "perfect games"
* Use Notion API to write games data to a database
* Use Notion API to mark in the database which games are no longer perfect
* Use Github Actions to schedule this as a daily job


# References

