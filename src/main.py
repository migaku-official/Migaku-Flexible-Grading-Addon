# -*- coding: utf-8 -*-
# 
from os.path import  join, dirname
import re
import aqt
from anki.utils import bodyClass, stripHTML
from anki.hooks import addHook, wrap, runHook, runFilter
from aqt import mw
from aqt import DialogManager
from .miutils import miInfo, miAsk
import requests 
import urllib.parse
import unicodedata
import json
import time
from aqt.tagedit import TagEdit
from aqt.main import AnkiQt
from aqt.qt import *
from aqt.reviewer import Reviewer
from pathlib import Path
from aqt.sound import clearAudioQueue, getAudio, play, playFromText
from aqt.utils import (
    askUserDialog,
    downArrow,
    mungeQA,
    qtMenuShortcutWorkaround,
    tooltip,
)
from anki.utils import isWin

def getConfig():
    return mw.addonManager.getConfig(__name__)

enablePassFail = "Enable Pass/Fail"
disablePassFail = "Disable Pass/Fail"
passFailSetting = None
onlyPassFail = getConfig()['passFail']


def saveConfig():
    newConf = {   "passFail": onlyPassFail }
    mw.addonManager.writeConfig(__name__, newConf)

def maybeReset():
    if mw.state == 'review':
        mw.reset()

def togglePassFail():
    global onlyPassFail
    if onlyPassFail:
        passFailSetting.setText(enablePassFail)
        onlyPassFail = False
        saveConfig()
        maybeReset()
    else:
        passFailSetting.setText(disablePassFail)
        onlyPassFail = True
        saveConfig()
        maybeReset()

def setupGuiMenu():
    global passFailSetting
    addMenu = False
    if not hasattr(mw, 'MigakuMainMenu'):
        mw.MigakuMainMenu = QMenu('Migaku',  mw)
        addMenu = True
    if not hasattr(mw, 'MigakuMenuSettings'):
        mw.MigakuMenuSettings = []
    if not hasattr(mw, 'MigakuMenuActions'):
        mw.MigakuMenuActions = []
    
    if onlyPassFail:
        label = disablePassFail
    else:   
        label = enablePassFail

    passFailSetting = QAction(label, mw)
    passFailSetting.triggered.connect(togglePassFail)
    mw.MigakuMenuSettings.append(passFailSetting)

    mw.MigakuMainMenu.clear()
    for act in mw.MigakuMenuSettings:
        mw.MigakuMainMenu.addAction(act)
    mw.MigakuMainMenu.addSeparator()
    for act in mw.MigakuMenuActions:
        mw.MigakuMainMenu.addAction(act)

    if addMenu:
        mw.form.menubar.insertMenu(mw.form.menuHelp.menuAction(), mw.MigakuMainMenu)

setupGuiMenu()

fred = '#c33'
darkgreen = '#008000'
red = '#E60000'
gray = '#e65c00'
green = '#00802B'
blue = '#005CE6'
answerButtonWidth = 'width: 90px  !important;'
if not isWin:
    answerButtonWidth = ''

miCSS = '''<style>

#outer{
    display: flex;
    align-items: center;
}

body {
    margin: 0px;
    padding: 0;
}

button {
    min-width: 60px;
    white-space: nowrap;
    margin: 0px;
}

.hitem {
    margin-top: 0px;
}

.stat {
    padding-top: 0px;
}

.stat2 {
    padding-top: 0px;
    font-weight: normal;
}

.stattxt {
    padding-left: 0px;
    padding-right: 0px;
    white-space: nowrap;
}

#ansbut { margin-bottom: 0px; }

.nobold {
    font-weight: normal;
    display: block;
    padding-top: 0px;
}

.spacer {
    height: 0px;
}

.spacer2 {
    height: 0px;
}

#outer {
    border-top: 1px solid #aaa;
    overflow: hidden  !important;
}

#innertable {
    padding: 0px;
}

.moreTD{
    padding-right:5px;
}

.editTD{
    padding-left:5px;
}

button{
    height: 24px !important;
}

.miShowAnswerButton{
    ''' + answerButtonWidth + '''
    padding-top: 0px !important;
    padding-bottom: 0px !important;
}

.answerBackButton{
   width:106px !important;
}

.answerNextIvlLeft, .questionNextIvlLeft, .answerNextIvlRight, .questionNextIvlRight{
    width:50px;
}


.answerNextIvlLeft{
    position:relative  !important;
    right:23px  !important;
}

.answerNextIvlRight{
    position:relative !important;
    left:23px !important;
}

#answerRemaining{
    position: absolute;
    width : 100vw;
    top : 4.5px;
    text-align: center;
}

.arHidden{
    display: none;
}

%s
</style>'''

def getLanguageLabel(language):
    if language == 'ja':
        return "外れ", "当たり"
    else:
        return "Fail", "Pass"
        
def getCss(language, answer = False):
    if answer:
        if language == 'ja':
            return '<b style="color:'+fred +';font-family:游明朝;font-weight: 400;">%s</b>', '<b style="color:'+darkgreen+';font-family:游明朝;font-weight: 400;">%s</b>'
        else:
            return '<b style="color:'+fred +';font-weight: 400;">%s</b>', '<b style="color:'+darkgreen+';font-weight: 400;">%s</b>'
    else:
        if language == 'ja':
            return '<b style="color:'+fred +';font-family:游明朝;font-weight: 400;">%s</b>', '<b style="color:'+darkgreen+';font-family:游明朝;font-weight: 400;">%s</b>'
        else:
            return '<b style="color:'+fred +';font-weight: 400;">%s</b>', '<b style="color:'+darkgreen+';font-weight: 400;">%s</b>'

def getPassValue(cnt):
    if cnt == 4:
        passValue = 3
    else:
        passValue = 2
    return passValue

def miButtonList(self):
    cnt = self.mw.col.sched.answerButtons(self.card)
    if self.state == 'question':
        if onlyPassFail:
            language = mw.pm.meta["defaultLang"]
            fail, passe = getLanguageLabel(language)
            failCss, passeCss = getCss(language, False)
            return ((1, getAdjustedCss() + failCss%fail),) + ((0, "showAnswer"), (getPassValue(cnt), passeCss%passe))
        else:
            return getDefaulButtons(cnt, True)
    else:

        if onlyPassFail:
            language = mw.pm.meta["defaultLang"]
            fail, passe = getLanguageLabel(language)
            failCss, passeCss = getCss(language, True)
            return ((1,  getAdjustedCss() +  failCss%fail),) + ((getPassValue(cnt), passeCss%passe),)
        else:
            return getDefaulButtons(cnt)

def getAdjustedCss():
    if not mw.col.conf["estTimes"] and not mw.col.conf["dueCounts"]:
        return miCSS%'#outer{  height:34px;}'
    elif not mw.col.conf["estTimes"] and mw.col.conf["dueCounts"]: 
        return miCSS%'#outer{ height: 50px !important;} td button{ margin-top: 18px;} .miShowAnswer button{ margin-top: 0px;} .miShowAnswer .stattxt{margin-bottom:2px;}'
    elif mw.col.conf["estTimes"] and not mw.col.conf["dueCounts"]: 
        return miCSS%'#outer{ height: 50px !important;} .editTD button, .moreTD button{ margin-top: 18px;} .miShowAnswer button{ margin-top: 18px;} .nextDueIvl button{margin-top: 2px;}'
    else:
        return miCSS%'#outer{ height: 50px !important;} .editTD button, .moreTD button{ margin-top: 18px;} .miShowAnswer button{ margin-top: 0px;} .miShowAnswer .stattxt{margin-bottom:2px;} .nextDueIvl button{margin-top: 2px;}'

def getDefaulButtons(cnt, showAnswer = False):
    l = ((1, getAdjustedCss() + '<b style="color:'+red +';font-weight: 400;">%s</b>'%_("Again")),)
    if cnt == 2:
        good = ((2, '<b style="color:'+green +';font-weight: 400;">%s</b>'%_("Good")),)
    elif cnt == 3:
        good = ((2, '<b style="color:'+green +';font-weight: 400;">%s</b>'%_("Good")),)
        easy = ((3, '<b style="color:'+blue +';font-weight: 400;">%s</b>'%_("Easy")),)
    else:   
        hard = ((2, '<b style="color:'+gray +';font-weight: 400;">%s</b>'%_("Hard")),)
        good = ((3, '<b style="color:'+green +';font-weight: 400;">%s</b>'%_("Good")),)
        easy = ((4, '<b style="color:'+blue +';font-weight: 400;">%s</b>'%_("Easy")),)
    if showAnswer:
        showAnswerButton = ((0, "showAnswer"),)
        if cnt == 2:
            return l + showAnswerButton + good
        elif cnt == 3:
            return l + showAnswerButton + good + easy
        else:   
            return l + hard + showAnswerButton + good + easy
    else:
        if cnt == 2:
            return l + good
        elif cnt == 3:
            return l + good + easy
        else:   
            return l + hard + good + easy

def miAnswerButtons(self):

        if self.state == 'question':
            buf = getBuf(self)
            if self.card.shouldShowTimer():
                maxTime = self.card.timeLimit() / 1000
            else:
                maxTime = 0
            self.bottom.web.eval("showQuestion(%s,%d);" % (json.dumps(buf), maxTime))
            self.bottom.web.adjustHeightToFit()
        elif self.state == 'answer':
            buf = getBuf(self)
            script = """
    <script>$(function () { $("#defease").focus(); });</script>"""



            return buf + script

def getShortcut(i):
    if i == 3 and onlyPassFail:
        i = 2
    return i

def getBuf(self):
    default = self._defaultEase()
    def but(i, label, count):
            if i == default:
                extra = "id=defease"
            else:
                extra = ""
            due = self._buttonTime(i, count)
            if not onlyPassFail or (onlyPassFail and self.state == 'question'):
                return """
    <td class="nextDueIvl"  align=center>%s<button %s title="%s" data-ease="%s" onclick='pycmd("ease%d");'>\
    %s</button></td>""" % (
                    due,
                    extra,
                    _("Shortcut key: %s") % getShortcut(i),
                    i,
                    i,
                    label,
                )
            else:
                return """
    <td class="nextDueIvl"  align=center>%s<button class="answerBackButton" %s title="%s" data-ease="%s" onclick='pycmd("ease%d");'>\
    %s</button></td>""" % (
                    due,
                    extra,
                    _("Shortcut key: %s") % getShortcut(i),
                    i,
                    i,
                    label,
                )
       
    def showAnswersButton():
            return """
<td class="miShowAnswer"  class=stat2 align=center><div class=stattxt>%s</div>
<button  class="miShowAnswerButton" title="%s" id=ansbut onclick='pycmd("ans");'>%s</button></td>""" % (
            self._remaining(),
            _("Shortcut key: %s") % _("Space"),
            _("Show Answer"),
        )

    buf = "<center><table cellpading=0 cellspacing=0><tr>"
    count = 0;
    for ease, label in self._answerButtonList():
        if label == "showAnswer":
            buf += showAnswersButton()
        else:
            buf += but(ease, label, count)
        count += 1
    buf += "</tr></table>"
    return buf

def miShortcutKeys(self):
        if onlyPassFail:
            return [
                ("e", self.mw.onEditCurrent),
                (" ", self.onEnterKey),
                (Qt.Key_Return, self.onEnterKey),
                (Qt.Key_Enter, self.onEnterKey),
                ("r", self.replayAudio),
                (Qt.Key_F5, self.replayAudio),
                ("Ctrl+1", lambda: self.setFlag(1)),
                ("Ctrl+2", lambda: self.setFlag(2)),
                ("Ctrl+3", lambda: self.setFlag(3)),
                ("Ctrl+4", lambda: self.setFlag(4)),
                ("*", self.onMark),
                ("=", self.onBuryNote),
                ("-", self.onBuryCard),
                ("!", self.onSuspend),
                ("@", self.onSuspendCard),
                ("Ctrl+Delete", self.onDelete),
                ("v", self.onReplayRecorded),
                ("Shift+v", self.onRecordVoice),
                ("o", self.onOptions),
                ("1", lambda: self._answerCard(1)),
                ("2", lambda: self._answerCard(3))
            ]
        else:
            return [
                ("e", self.mw.onEditCurrent),
                (" ", self.onEnterKey),
                (Qt.Key_Return, self.onEnterKey),
                (Qt.Key_Enter, self.onEnterKey),
                ("r", self.replayAudio),
                (Qt.Key_F5, self.replayAudio),
                ("Ctrl+1", lambda: self.setFlag(1)),
                ("Ctrl+2", lambda: self.setFlag(2)),
                ("Ctrl+3", lambda: self.setFlag(3)),
                ("Ctrl+4", lambda: self.setFlag(4)),
                ("*", self.onMark),
                ("=", self.onBuryNote),
                ("-", self.onBuryCard),
                ("!", self.onSuspend),
                ("@", self.onSuspendCard),
                ("Ctrl+Delete", self.onDelete),
                ("v", self.onReplayRecorded),
                ("Shift+v", self.onRecordVoice),
                ("o", self.onOptions),
                ("1", lambda: self._answerCard(1)),
                ("2", lambda: self._answerCard(2)),
                ("3", lambda: self._answerCard(3)),
                ("4", lambda: self._answerCard(4)),
            ]
    
def AKR_answerCard(self, ease):
    cnt = mw.col.sched.answerButtons(mw.reviewer.card)  # Get button count

    try:
        ease = remap[cnt][ease]
    except (KeyError, IndexError):
        pass

    __oldFunc(self, ease)

def miShowQuestion(self):
        self._reps += 1
        self.state = "question"
        self.typedAnswer = None
        c = self.card
        if c.isEmpty():
            q = _(
                """\
The front of this card is empty. Please run Tools>Empty Cards."""
            )
        else:
            q = c.q()
        if self.autoplay(c):
            playFromText(q)
        q = self._mungeQA(q)
        q = runFilter("prepareQA", q, c, "reviewQuestion")

        bodyclass = bodyClass(self.mw.col, c)

        self.web.eval("_showQuestion(%s,'%s');" % (json.dumps(q), bodyclass))
        self._drawFlag()
        self._drawMark()
        self._answerButtons()
        if self.typeCorrect:
            self.mw.web.setFocus()
        runHook("showQuestion")

def miAnswerCard(self, ease):
        cnt = self.mw.col.sched.answerButtons(self.card)
        if onlyPassFail and (cnt == 2 or cnt == 3) and ease == 3:
            ease = 2
        "Reschedule card and show next."
        if self.mw.state != "review":
            return
        if self.mw.col.sched.answerButtons(self.card) < ease:
            miInfo('failing here')
            return
        self.mw.col.sched.answerCard(self.card, ease)
        self._answeredIds.append(self.card.id)
        self.mw.autosave()
        self.nextCard()

def miButtonTime(self, i, count = False):
    if onlyPassFail and self.state == 'answer':
        if not self.mw.col.conf["estTimes"]:
            return "<div class=spacer></div>"
        if count == 0:
            className = 'answerNextIvlLeft'
        else:
            className = 'answerNextIvlRight'
        txt = self.mw.col.sched.nextIvlStr(self.card, i, True) or "&nbsp;"
        return '<div class="nobold ' + className +'">%s</div>' % txt
    else:
        
        if count == 0:
            className = 'questionNextIvlLeft'
        else:
            className = 'questionNextIvlRight'
        if not self.mw.col.conf["estTimes"]:
            return "<div class=spacer></div>"
        txt = self.mw.col.sched.nextIvlStr(self.card, i, True) or "&nbsp;"
        return '<div class="nobold ' + className +'">%s</div>' % txt

def insertRemaining(self):
    if onlyPassFail or (not mw.col.conf["estTimes"] and mw.col.conf["dueCounts"]):
        self.bottom.web.eval("""document.body.innerHTML += '<div class="arHidden" id="answerRemaining">"""+ self._remaining() + "</div>'")

def showRemaining(self):
    remaining = self._remaining()
    if 'nm_state_on' in  self.mw.pm.profile:
        if mw.pm.profile['nm_state_on']:
            remaining = remaining.replace(' + ', '<span style="color:#C8CAC9;"> + </span>')
    self.bottom.web.eval("""var answerRemaining = document.getElementById('answerRemaining');
        answerRemaining.innerHTML= '"""+  remaining +"""';
        if(answerRemaining.classList.contains('arHidden')){
            answerRemaining.classList.remove('arHidden');
        }
        """)
def hideRemaining(self):
    self.bottom.web.eval("""var answerRemaining = document.getElementById('answerRemaining');
        if(!answerRemaining.classList.contains('arHidden')){
            answerRemaining.classList.add('arHidden');
        }
        """)

def cleanStructure(html):
    return html.replace('<br>', '').replace('<td align=left width=50 valign=top class=stat>', '<td align=left width=50 valign=top class="stat editTD">').replace('<td width=50 align=right valign=top class=stat>', '<td width=50 align=right valign=top class="stat moreTD">').replace('valign=top', 'valign=middle')

def miInitWeb(self):
        self._reps = 0
        self.web.stdHtml(
            self.revHtml(),
            css=["reviewer.css"],
            js=[
                "jquery.js",
                "browsersel.js",
                "mathjax/conf.js",
                "mathjax/MathJax.js",
                "reviewer.js",
            ],
        )
        self.bottom.web.show()
        cleanedHtml = cleanStructure(self._bottomHTML())
        self.bottom.web.stdHtml(
            cleanedHtml,
            css=["toolbar-bottom.css", "reviewer-bottom.css"],
            js=["jquery.js", "reviewer-bottom.js"],
        )

def miShowQuestionNoAudio(self):
        self._reps += 1
        self.state = "question"
        self.typedAnswer = None
        c = self.card
        if c.isEmpty():
            q = _(
                """\
The front of this card is empty. Please run Tools>Empty Cards."""
            )
        else:
            q = c.q()
        q = self._mungeQA(q)
        q = runFilter("prepareQA", q, c, "reviewQuestion")

        bodyclass = bodyClass(self.mw.col, c)

        self.web.eval("_showQuestion(%s,'%s');" % (json.dumps(q), bodyclass))
        self._drawFlag()
        self._drawMark()
        self._answerButtons()
        if self.typeCorrect:
            self.mw.web.setFocus()
        runHook("showQuestion")

def replaceNoAudioMethod():
    if hasattr(mw.reviewer, 'showQuestionWithoutAudio'):
        mw.reviewer.showQuestionWithoutAudio = miShowQuestionNoAudio

addHook('profileLoaded', replaceNoAudioMethod)   

Reviewer._buttonTime = miButtonTime 
Reviewer._answerCard = miAnswerCard
Reviewer._showQuestion = miShowQuestion
Reviewer._answerButtons = miAnswerButtons
Reviewer._shortcutKeys = miShortcutKeys
Reviewer._answerButtonList = miButtonList
Reviewer._initWeb = miInitWeb
Reviewer._initWeb = wrap(Reviewer._initWeb, insertRemaining)
Reviewer._showAnswer = wrap(Reviewer._showAnswer, showRemaining)
Reviewer._showQuestion = wrap(Reviewer._showQuestion, hideRemaining)
