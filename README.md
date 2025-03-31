# imdash

This library builds on [imviz](https://github.com/joruof/imviz) to create interactive dashboards.

Data from files, ros2 topics, or [structstores](https://github.com/mertemba/structstore) can be displayed and manipulated.


### Aduulm Repository Metadata

- last updated: 02/2025
- name: imdash
- category: tooling
- maintainers: Marco Deuscher
- license: Apache-2.0
- HW dependencies: none


### Usage

Install with ```pip install .``` and launch with the ```imdash``` command.


### Views, Components, and Connectors

The imdash library specifies three basic application building blocks:

**Views** render (at least) one window and can hold multiple *components*.
(e.g. View2D provides a window for plotting).

**Components** are sub-elements, which extend the functionality of a view.
(e.g. Value2DComponent plots values on a View2D, History2DComponent plots value histories on a View2D)

**Connectors** are classes, which provide access to some kind of data source.
(e.g. Ros2Connector can subscribe to ros2 topics, FilesystemConnector can read in files)


### Writing Extensions

New views, components and connectors can be defined by creating sub classes,
which extend the respective base classes:

- Views extend `imdash.utils.ViewBase`
- Components extend the view's component base class e.g. `imdash.views.view_2d.View2DComponent`
- Connectors extend `imdash.connectors.ConnectorBase`

By deriving from these base classes the extension is automatically registered.
Note that, new classes *must be imported* to be found by imdash.

In the simplest case, just import your new classes and then run the imdash main.

```python

# import or define your extension here
import ...

from imdash.main import main

if __name__ == '__main__':
    main()
```
