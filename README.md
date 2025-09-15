# Invite Link
https://discord.com/oauth2/authorize?client_id=1416127534852083902&permissions=549755840512&integration_type=0&scope=bot

# General

With Discord Study Leaderboard Bot (DSLB), you can track you study time inside Discord and compete with your friends.
The goal of this project was to create an accessible and free (as in free-software) application to encourage students to help each other by checking on how much their friends have studied.

---

# Commands
Every user has 10 free lobby slots for now.

## create_lobby
Creates a lobby with the given name and assigns the author as admin. If the lobby is set to private, then the bot will send the user a private message to assign the password to the lobby (make sure DMs are enabled!).

## join_lobby
Lets the user join a lobby with the given name. If the lobby is private, the bot will send the user a private message to confirm the password of the lobby (make sure DMs are enabled!).

## my_lobbies
Lists the lobbies the user has joined/created.

## start/stop_chrono
Starts/Stops a chronometer for a given lobby name only if the user is in the said lobby.

## leave_lobby (not implemented yet)
Lets the user leave a lobby with the given name.

## kick_from_lobby (not implemented yet)
Lets the user kick another user from a lobby. (requires admin role in the lobby)

## promote_user (not implemented yet)
Lets the user promote another user to admin in a lobby. (requires admin role in the lobby)

## reset_lobby (not implemented yet)
Lets the user reset all of the saved times in a lobby. (requires admin role in the lobby)

## delete_lobby (not implemented yet)
Lets the user delete a lobby. (requires admin role in the lobby)

## rename_lobby (not implemented yet)
Lets the user rename a lobby. (requires admin role in the lobby)

---

# How to help the project

## Devs
Since I didn't have enough time at my hands while creating the project, as you might have noticed, the project structure is mostly sphagetti. So a major refactor is needed for future development. I also didn't have time to properly write test cases...

---

# Disclaimer of AI usage

This project was (initially) mostly written by AI under the author's supervision. The generated code was then carefully checked and edited by hand.
