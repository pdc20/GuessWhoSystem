from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5 import uic

import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

import sys
from random import *


class DisplayWindow(QMainWindow):
    """Class that contains the widgets of the backend window GUI. No code should go in here except for functionality
        involving only the widgets and nothing else."""

    def __init__(self):
        super(DisplayWindow, self).__init__()
        uic.loadUi("UIs/streamGUI.ui", self)

    def areComboBoxesEmpty(self):
        return self.guesserCombo.currentIndex() == 0 or \
               self.checkerNicknameCombo.currentIndex() == 0 or \
               self.checkerPlayerNameCombo.currentIndex() == 0


class BackendWindow(QMainWindow):
    """Class that contains the widgets of the main window GUI. No code should go in here except for functionality
        involving only the widgets and nothing else."""

    def __init__(self):
        super(BackendWindow, self).__init__()
        uic.loadUi("UIs/backend.ui", self)

    def clearPlayerSettingsFields(self):
        self.playerBox.clear()
        self.livesLeftBox.clear()
        self.playerLogList.clear()


class Spreadsheet:
    """Class that contains spreadsheet information retrieved from Google Sheets."""

    def __init__(self):
        self.SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

    def initialise(self, spreadsheetID, credentialsPath):
        self.spreadsheetID = spreadsheetID
        self.credentialsPath = credentialsPath
        creds = None
        try:
            if os.path.exists(f"{self.credentialsPath}\\token.json"):
                creds = Credentials.from_authorized_user_file(f"{self.credentialsPath}\\token.json", self.SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        f"{self.credentialsPath}\\credentials.json", self.SCOPES)
                    creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open(f"{self.credentialsPath}\\token.json", 'w') as token:
                    token.write(creds.to_json())

            self.service = build('sheets', 'v4', credentials=creds)
        except Exception as e:
            print(e) # temporary. Will make this into a popup alert.

    def query(self, rangeQuery):
        # Call the Sheets API
        try:
            sheet = self.service.spreadsheets()
            result = sheet.values().get(spreadsheetId=self.spreadsheetID,
                                        range=rangeQuery).execute()
            values = result.get('values', [])
            return values
        except Exception as e:
            print(e) # Temporary. Plan on making this a popup alert.
            return None


class Player:
    """Class containing data on a player."""

    class PlayerLogEntry:
        def __init__(self, bracketRound, guesser, guessedPlayer, guessedIdentity, isGuessCorrect):
            self.bracketRound = bracketRound
            self.guesser = guesser
            self.guessedPlayer = guessedPlayer
            self.guessedIdentity = guessedIdentity
            self.isGuessCorrect = isGuessCorrect
            self.verdict = "MATCH" if isGuessCorrect else "INCORRECT"

        def __str__(self):
            return f"On round {self.bracketRound}, player {self.guesser.nickname} guessed {self.guessedPlayer.nickname} was {self.guessedIdentity.handle}. Result: {self.verdict}"

    def __init__(self, id, handle, nickname, character, hostStatus, remarks):
        self.id = id
        self.handle = handle
        self.nickname = nickname
        self.character = character
        self.hostStatus = hostStatus
        self.remarks = remarks

        self.lives = 2
        self.playHistory = []


class MainApp(QApplication):
    def __init__(self, debug=False):
        super(MainApp, self).__init__(sys.argv)
        self.spreadsheet = Spreadsheet()
        self.displayWindow = DisplayWindow()
        self.backendWindow = BackendWindow()
        self.displayWindow.show()
        self.backendWindow.show()

        self.backendWindow.dataUpdateButton.clicked.connect(self.dataUpdateButtonClicked)
        self.backendWindow.nicknameCombo.activated.connect(self.nicknameComboActivated)
        self.displayWindow.checkButton.clicked.connect(self.checkButtonClicked)

        if debug:
            self.performDebugOperations()

    def checkButtonClicked(self):
        # First ensure that all the comboboxes are not on index 0 (Select...)
        if self.displayWindow.areComboBoxesEmpty(): return
        # Check whether the guess is correct
        if self.players[self.displayWindow.checkerNicknameCombo.currentIndex() - 1].handle == self.displayWindow.checkerPlayerNameCombo.currentText():
            self.displayWindow.checkerVerdictLabel.setText("MATCH!")
        else: self.displayWindow.checkerVerdictLabel.setText("INCORRECT")

    def nicknameComboActivated(self):
        index = self.backendWindow.nicknameCombo.currentIndex()
        if index == 0:
            self.backendWindow.clearPlayerSettingsFields()
            return
        player = self.players[index - 1]
        self.backendWindow.playerBox.setText(player.handle)
        self.backendWindow.livesLeftBox.setText(f"{player.lives}")
        self.backendWindow.playerLogList.addItems([str(x) for x in player.playHistory])

    def performDebugOperations(self):
        # Replace this stuff with where your credentials file is and hte link to the spreadsheet.
        self.backendWindow.spreadsheetIDLine.setText("1Wv7VAic0Rl35od4c7qIEywZAZsArwxWFakllr-N3MiE")
        self.backendWindow.credentialsLine.setText("C:\\Users\\_Kookie\\Documents\\guesswhocredentials")
        self.backendWindow.streamDirectoryLine.setText("C:\\Users\\_Kookie\\Documents\\guesswhocredentials")
        self.backendWindow.dataRangeLine.setText("Form responses 1!A2:G")
        self.backendWindow.dataUpdateButton.click()

    def dataUpdateButtonClicked(self):
        # First check if all the fields are filled in.
        if not (self.backendWindow.spreadsheetIDLine.text().strip() and
                self.backendWindow.credentialsLine.text().strip() and
                self.backendWindow.dataRangeLine.text().strip() and
                self.backendWindow.streamDirectoryLine.text().strip()):
            self.backendWindow.dataStatusLabel.setText("Some fields are empty!")
            return
        # Store the data in this app.
        self.backendWindow.dataStatusLabel.setText("Updating...")
        self.updateSpreadsheetDetails()
        self.loadFromSpreadsheet()
        self.loadCombo(self.backendWindow.nicknameCombo, [player.nickname for player in self.players])
        self.loadCombo(self.displayWindow.guesserCombo, [player.nickname for player in self.players])
        self.loadCombo(self.displayWindow.checkerNicknameCombo, [player.nickname for player in self.players])

        l = [player.handle for player in self.players]
        shuffle(l)
        self.loadCombo(self.displayWindow.checkerPlayerNameCombo, l)

    def loadCombo(self, comboBox, entries):
        comboBox.clear()
        comboBox.addItem("Select...")
        comboBox.addItems(entries)


    def updateSpreadsheetDetails(self):
        self.spreadsheet.initialise(self.backendWindow.spreadsheetIDLine.text(),
                                    self.backendWindow.credentialsLine.text())
        self.streamDirectory = self.backendWindow.streamDirectoryLine.text()

    def loadFromSpreadsheet(self):
        """Loads the data from the google sheet to this app."""
        self.rawData = self.spreadsheet.query(self.backendWindow.dataRangeLine.text())

        if not self.rawData:
            self.backendWindow.dataStatusLabel.setText("Updated, but no data found.")
        else:
            self.backendWindow.dataStatusLabel.setText("Successfully updated!")
            # Load data.
            self.players = []
            id = 0
            for row in self.rawData:
                handle = row[1]
                nickname = row[2]
                character = row[3]
                hostStatus = row[4]
                remarks = None
                try:
                    remarks = row[6]
                except:
                    pass
                self.players.append(Player(id, handle, nickname, character, hostStatus, remarks))
            # Want to sort the players in alphabetical order by nickname for easier reference.
            self.players.sort(key=lambda x: x.nickname.lower())
            for i in range(len(self.players)):
                self.players[i].id = i


app = MainApp(True)
app.exec()
