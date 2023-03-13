class ConnectorBase:
    """
    Inherit from this class to marks a type as source connector.

    Child classes will get instantiated automatically by the SourcesManager as singletons.
    Thus, child classes don't need to be instantiated explicity.
    """

    def __init__(self, prefix):
        # this prefix must be added to the source paths of this connector
        # it is used to select the respective connector type
        # the prefix must be unique among all connectors
        self.prefix = prefix

    def cleanup(self):
        # called on reinit
        pass

    def render(self, views, sources):
        # render the sources selection menu
        pass

    def update_sources(self, sources):
        # update the sources belonging to this connector
        pass
