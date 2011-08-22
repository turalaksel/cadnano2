
#ifndef ELLIPSEITEM_H
#define ELLIPSEITEM_H


// QT_MODULE(Gui)

#include <QtGui/qgraphicsitem.h>
#include <QtGui/qgraphicswidget.h>
// #include <QtGui/qstyleoptiongraphicsitem.h>
#include <QtGui/qpainter.h>

QT_BEGIN_NAMESPACE
class QGraphicsItem;
class QGraphicsEllipseItem;
class QWidget;
class QStyleOptionGraphicsItem;
class QPainter;
QT_END_NAMESPACE

class GraphicsEllipseItem : public QGraphicsEllipseItem {
    // This is needed by the Qt Meta-Object Compiler.
    Q_OBJECT
    
    public:
        GraphicsEllipseItem (QGraphicsItem *parent = 0);
        virtual ~GraphicsEllipseItem ();
        virtual void paint(QPainter *painter, const QStyleOptionGraphicsItem *option, QWidget *widget = 0); 
    
#endif