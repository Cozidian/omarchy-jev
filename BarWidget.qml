import QtQuick
import qs.Commons
import qs.Ui as Ui

Ui.BarWidget {
    id: root
    moduleName: "io.github.cozidian.jev"
    implicitWidth: button.implicitWidth
    implicitHeight: button.implicitHeight
    Ui.WidgetButton {
        id: button
        anchors.fill: parent
        bar: root.bar
        text: "JEV"
        tooltipText: "Ask JEV · Super+Alt+J"
        onPressed: function(buttonCode) {
            if (buttonCode === Qt.LeftButton && root.bar && root.bar.shell)
                root.bar.shell.toggle(root.moduleName, "{}")
        }
    }
}
