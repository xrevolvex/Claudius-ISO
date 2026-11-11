/* Claudius installer slideshow (shown while files are copied) */
import QtQuick 2.0;
import calamares.slideshow 1.0;

Presentation
{
    id: presentation

    function nextSlide() { presentation.goToNextSlide(); }

    Timer {
        id: advanceTimer
        interval: 7000
        running: presentation.activatedInCalamares
        repeat: true
        onTriggered: nextSlide()
    }

    Slide {
        Rectangle { anchors.fill: parent; color: "#0d1122" }
        Image { id: logo1; source: "logo.png"; width: 110; height: 110; fillMode: Image.PreserveAspectFit
                anchors.horizontalCenter: parent.horizontalCenter; y: parent.height * 0.18 }
        Text { anchors.top: logo1.bottom; anchors.topMargin: 24; anchors.horizontalCenter: parent.horizontalCenter
               text: "Installing Claudius"; color: "#ffffff"; font.pixelSize: 28; font.bold: true }
        Text { anchors.horizontalCenter: parent.horizontalCenter; y: parent.height * 0.62; width: parent.width * 0.7
               horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap; color: "#c8cde0"; font.pixelSize: 16
               text: "Light, fast and yours. This takes a few minutes, so sit back." }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0d1122" }
        Text { anchors.centerIn: parent; width: parent.width * 0.75; horizontalAlignment: Text.AlignHCenter
               wrapMode: Text.WordWrap; color: "#e6e9f2"; font.pixelSize: 18; textFormat: Text.RichText
               text: "<b style='color:#ffb547'>Tuned for your machine</b><br><br>Every boot, Claudius checks your RAM and picks the lite, balanced or performance profile for it automatically." }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0d1122" }
        Text { anchors.centerIn: parent; width: parent.width * 0.75; horizontalAlignment: Text.AlignHCenter
               wrapMode: Text.WordWrap; color: "#e6e9f2"; font.pixelSize: 18; textFormat: Text.RichText
               text: "<b style='color:#ffb547'>Thousands of apps</b><br><br>Claudius is built on Debian. Open a terminal and type <i>claudius install gimp</i>, or use Synaptic from the menu." }
    }
    Slide {
        Rectangle { anchors.fill: parent; color: "#0d1122" }
        Text { anchors.centerIn: parent; width: parent.width * 0.75; horizontalAlignment: Text.AlignHCenter
               wrapMode: Text.WordWrap; color: "#e6e9f2"; font.pixelSize: 18; textFormat: Text.RichText
               text: "<b style='color:#ffb547'>Open source</b><br><br>Every line that builds Claudius is on GitHub. Fork it, change it, make it yours." }
    }

    function onActivate() { presentation.currentSlide = 0; }
    function onLeave() { }
}
