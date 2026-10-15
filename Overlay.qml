import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import QtQuick
import QtQuick.Controls
import qs.Commons as Commons

Item {
    id: root
    property var shell: null
    property var manifest: null
    property string omarchyPath: ""
    property bool opened: false
    property bool preview: false
    property bool browsing: false
    property string pending: ""
    property int generation: 0
    property string heading: "What would you like to do?"
    property string detail: "Ask naturally, or browse the available actions."
    property string outcome: ""
    property var entries: []
    property var filtered: []
    property int omarchyCount: 0
    property int shortcutCount: 0
    readonly property string pluginDir: manifest && manifest.__sourceDir
        ? manifest.__sourceDir : String(Qt.resolvedUrl(".")).replace(/^file:\/\//, "").replace(/\/$/, "")

    function fade(color, opacity) { return Qt.rgba(color.r, color.g, color.b, opacity) }
    function open(payloadJson) {
        root.opened = true
        root.browsing = false
        input.text = ""
        root.heading = "What would you like to do?"
        root.detail = "Try “my eyes feel tired”, “brightness to 45%” or “remind me to stretch in twenty minutes”."
        root.outcome = ""
        if (!discovery.running) discovery.running = true
        Qt.callLater(function() { input.forceActiveFocus() })
    }
    function close() {
        root.opened = false
        root.generation += 1
        deadline.stop()
        worker.running = false
        discovery.running = false
    }
    function dismiss() {
        close()
        if (shell && typeof shell.hide === "function") shell.hide("io.github.cozidian.jev")
    }
    function status(payloadJson) {
        return JSON.stringify({opened: root.opened, browsing: root.browsing, count: root.entries.length,
            filtered: root.filtered.length, shortcutCount: root.shortcutCount, heading: root.heading, outcome: root.outcome,
            busy: worker.running, preview: root.preview})
    }
    function toggle() { if (opened) dismiss(); else open("{}") }
    function toggleBrowse() {
        if (worker.running) return
        root.browsing = !root.browsing
        input.text = ""
        root.filterCatalogue()
        input.forceActiveFocus()
    }
    function filterCatalogue() {
        var tokens = input.text.trim().toLowerCase().split(/\s+/).filter(function(t) { return t.length > 0 })
        root.filtered = root.entries.filter(function(row) {
            var haystack = (row.route + " " + row.group + " " + row.summary + " " + row.aliases.join(" ")).toLowerCase()
            return tokens.every(function(token) { return haystack.indexOf(token) !== -1 })
        })
        commandList.currentIndex = root.filtered.length ? 0 : -1
    }
    function inspect(row) {
        if (!row) return
        root.browsing = false
        input.text = row.route
        root.heading = row.label
        if (row.kind === "shortcut") {
            root.heading = row.chord
            root.detail = row.summary + "\nPress " + row.chord + (row.context || "") + ". JEV does not press keys."
            Qt.callLater(function() { input.forceActiveFocus(); input.cursorPosition = input.text.length })
            return
        }
        root.detail = row.summary + "\nUsage: " + row.route + (row.args ? " " + row.args : "")
            + "\n" + (row.mode === "automatic" ? "Press Enter to run, or enable Preview only first."
                : row.mode === "validated" ? "Add the desired operation or value to your request. Only validated safe options can run."
                : "Press Enter for guidance. This command cannot run automatically.")
        Qt.callLater(function() { input.forceActiveFocus(); input.cursorPosition = input.text.length })
    }
    function configureKey() {
        if (!worker.running && !configuration.running) configuration.running = true
    }
    function submit() {
        if (worker.running || !input.text.trim()) return
        if (root.browsing) {
            if (commandList.currentIndex >= 0) root.inspect(root.filtered[commandList.currentIndex])
            return
        }
        root.pending = JSON.stringify({text: input.text.trim(), requestId: ++root.generation})
        root.heading = root.preview ? "Finding an action…" : "Asking JEV…"
        root.detail = ""
        root.outcome = ""
        worker.command = ["python3", root.pluginDir + "/worker.py"].concat(root.preview ? ["--preview"] : [])
        worker.running = true
        deadline.restart()
    }
    Process {
        id: discovery
        command: ["python3", root.pluginDir + "/worker.py", "--catalogue"]
        stdout: StdioCollector {
            onStreamFinished: {
                if (!root.opened) return
                try {
                    var data = JSON.parse(text)
                    if (!Array.isArray(data.entries)) throw new Error("Missing catalogue")
                    root.entries = data.entries
                    root.omarchyCount = data.omarchyCount
                    root.shortcutCount = data.shortcutCount || 0
                    root.filterCatalogue()
                } catch (e) {
                    root.heading = "Command catalogue unavailable"
                    root.detail = "Check that “omarchy commands --all --json” works, then reopen Nudge."
                }
            }
        }
        stderr: StdioCollector {}
    }
    Timer {
        id: deadline
        interval: 60000
        onTriggered: {
            root.generation += 1
            worker.running = false
            root.heading = "Request timed out"
            root.detail = "Check the desktop state before retrying; an action may have started."
            root.outcome = "error"
        }
    }
    Process {
        id: configuration
        command: ["python3", root.pluginDir + "/setup.py", "--launch"]
        onExited: function(exitCode, exitStatus) {
            if (exitCode === 0) root.dismiss()
            else {
                root.heading = "Could not open setup"
                root.detail = "Run python3 " + root.pluginDir + "/setup.py in a terminal."
                root.outcome = "error"
            }
        }
    }
    Process {
        id: worker
        stdinEnabled: true
        onStarted: { write(root.pending); stdinEnabled = false }
        onExited: function(exitCode, exitStatus) {
            stdinEnabled = true
            deadline.stop()
            if (root.opened && exitCode !== 0) {
                root.heading = "Could not complete the request"
                root.detail = "Check your connection and try again."
                root.outcome = "error"
            }
            if (root.opened) Qt.callLater(function() { input.forceActiveFocus(); input.selectAll() })
        }
        stdout: StdioCollector {
            onStreamFinished: {
                if (!root.opened) return
                try {
                    var result = JSON.parse(text)
                    if (result.requestId !== root.generation) return
                    root.heading = result.title
                    root.detail = result.detail
                    root.outcome = result.status
                    if (result.handoff) Qt.callLater(function() { root.dismiss() })
                } catch (e) {
                    root.heading = "Could not read the result"
                    root.detail = "Check the desktop state before trying again."
                    root.outcome = "error"
                }
            }
        }
        stderr: StdioCollector {}
    }
    PanelWindow {
        id: panel
        visible: root.opened
        anchors { top: true; bottom: true; left: true; right: true }
        color: "transparent"
        WlrLayershell.namespace: "omarchy-jev-launcher"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.Exclusive
        exclusionMode: ExclusionMode.Ignore
        Rectangle { anchors.fill: parent; color: "#66000000" }
        MouseArea { anchors.fill: parent; onClicked: root.dismiss() }
        Rectangle {
            id: card
            width: Math.min(760, panel.width - 48)
            height: Math.min(content.implicitHeight + 48, panel.height - 48)
            anchors.horizontalCenter: parent.horizontalCenter
            y: Math.max(24, (panel.height - height) * 0.25)
            radius: 18
            color: root.fade(Commons.Color.menu.background, 1)
            border.color: Commons.Color.menu.border
            border.width: 2
            MouseArea { anchors.fill: parent; onClicked: {} }
            Keys.onEscapePressed: root.dismiss()
            Column {
                id: content
                anchors { top: parent.top; left: parent.left; right: parent.right; margins: 24 }
                spacing: 16
                Row {
                    spacing: 12
                    Column {
                        spacing: 3
                        Text { text: "Nudge"; color: Commons.Color.menu.text; font.pixelSize: 16; font.bold: true }
                        Text { text: "Powered by JEV"; color: Commons.Color.menu.text; opacity: .6; font.pixelSize: 11 }
                    }
                    Text {
                        text: root.omarchyCount ? root.omarchyCount + " commands · " + root.shortcutCount + " shortcuts" : "Discovering Omarchy actions…"
                        color: Commons.Color.menu.text; opacity: .6; font.pixelSize: 13
                    }
                }
                TextField {
                    id: input
                    width: parent.width
                    height: 58
                    enabled: !worker.running
                    maximumLength: 800
                    placeholderText: root.browsing ? "Filter commands, shortcuts or descriptions…" : "Tell me what you need…"
                    placeholderTextColor: root.fade(Commons.Color.menu.text, .45)
                    color: Commons.Color.menu.text
                    selectionColor: Commons.Color.menu.selectedBackground
                    selectedTextColor: Commons.Color.menu.selectedText
                    font.pixelSize: 21
                    selectByMouse: true
                    leftPadding: 14
                    rightPadding: 14
                    background: Rectangle {
                        radius: 10
                        color: root.fade(Commons.Color.menu.text, .04)
                        border.color: input.activeFocus ? root.fade(Commons.Color.menu.text, .5) : Commons.Color.menu.border
                    }
                    onTextChanged: if (root.browsing) root.filterCatalogue()
                    onAccepted: root.submit()
                    Keys.onPressed: function(event) {
                        if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_B) {
                            root.toggleBrowse(); event.accepted = true
                        } else if ((event.modifiers & Qt.ControlModifier) && event.key === Qt.Key_K) {
                            root.configureKey(); event.accepted = true
                        } else if (root.browsing && (event.key === Qt.Key_Down || event.key === Qt.Key_Up)) {
                            var step = event.key === Qt.Key_Down ? 1 : -1
                            commandList.currentIndex = Math.max(0, Math.min(root.filtered.length - 1, commandList.currentIndex + step))
                            commandList.positionViewAtIndex(commandList.currentIndex, ListView.Contain)
                            event.accepted = true
                        }
                    }
                    Keys.onEscapePressed: root.dismiss()
                }
                Column {
                    visible: !root.browsing
                    width: parent.width
                    spacing: 10
                    Text {
                        width: parent.width
                        text: root.heading
                        textFormat: Text.PlainText
                        wrapMode: Text.Wrap
                        color: Commons.Color.menu.text
                        font.pixelSize: 18
                        font.bold: true
                    }
                    Flickable {
                        width: parent.width
                        height: Math.min(260, detailText.implicitHeight)
                        contentHeight: detailText.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        Text {
                            id: detailText
                            width: parent.width
                            text: root.detail
                            textFormat: Text.PlainText
                            wrapMode: Text.Wrap
                            color: Commons.Color.menu.text
                            opacity: .8
                            font.pixelSize: 15
                            lineHeight: 1.25
                        }
                    }
                }
                Column {
                    width: parent.width
                    visible: root.browsing
                    spacing: 8
                    Text {
                        text: root.filtered.length + " actions" + (input.text ? " match" : " · type to filter")
                        color: Commons.Color.menu.text; opacity: .6; font.pixelSize: 12
                    }
                    ListView {
                        id: commandList
                        width: parent.width
                        height: Math.min(360, panel.height * .38)
                        clip: true
                        model: root.filtered
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: ScrollBar {}
                        delegate: Rectangle {
                            id: commandRow
                            required property var modelData
                            required property int index
                            width: commandList.width
                            height: 82
                            radius: 8
                            color: commandList.currentIndex === index ? root.fade(Commons.Color.menu.text, .08) : "transparent"
                            Column {
                                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 12 }
                                spacing: 4
                                Text {
                                    width: parent.width
                                    text: commandRow.modelData.route
                                    textFormat: Text.PlainText
                                    color: Commons.Color.menu.text
                                    font.pixelSize: 15
                                    font.bold: true
                                    elide: Text.ElideRight
                                }
                                Text {
                                    width: parent.width
                                    text: commandRow.modelData.summary
                                    textFormat: Text.PlainText
                                    color: Commons.Color.menu.text
                                    font.pixelSize: 12
                                    opacity: .7
                                    elide: Text.ElideRight
                                }
                                Text {
                                    text: commandRow.modelData.label + (commandRow.modelData.hidden ? " · internal helper" : "")
                                    color: Commons.Color.menu.text
                                    font.pixelSize: 11
                                    opacity: .5
                                }
                            }
                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                onEntered: commandList.currentIndex = commandRow.index
                                onClicked: root.inspect(commandRow.modelData)
                            }
                        }
                    }
                    Text {
                        visible: root.filtered.length === 0
                        text: "No commands match. Try a group such as audio, theme or reminder."
                        color: Commons.Color.menu.text; opacity: .7; font.pixelSize: 13
                    }
                }
                Rectangle { width: parent.width; height: 1; color: Commons.Color.menu.border }
                Row {
                    width: parent.width
                    spacing: 16
                    Button {
                        text: root.browsing ? "Ask Nudge" : "Browse actions"
                        enabled: !worker.running
                        onClicked: root.toggleBrowse()
                    }
                    Button {
                        text: "Configure key"
                        enabled: !worker.running && !configuration.running
                        onClicked: root.configureKey()
                    }
                    CheckBox {
                        id: previewBox
                        text: "Preview only"
                        checked: root.preview
                        enabled: !worker.running
                        onToggled: root.preview = checked
                        contentItem: Text {
                            text: previewBox.text
                            color: Commons.Color.menu.text
                            font.pixelSize: 13
                            leftPadding: previewBox.indicator.width + previewBox.spacing
                            verticalAlignment: Text.AlignVCenter
                        }
                    }
                    Text {
                        text: root.browsing ? "↑↓ select · Enter inspect" : "Enter · " + (root.preview ? "preview" : "run safe action")
                        color: Commons.Color.menu.text; opacity: .55; font.pixelSize: 12
                        anchors.verticalCenter: parent.verticalCenter
                    }
                }
                Text {
                    width: parent.width
                    text: "New and destructive commands stay suggestion-only. Ctrl+B · browse · Esc · close"
                    wrapMode: Text.Wrap
                    color: Commons.Color.menu.text
                    opacity: .5
                    font.pixelSize: 11
                }
            }
        }
    }
}
