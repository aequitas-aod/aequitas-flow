"""
flow.py

This module defines a socio-technical modeling framework using sites, channels, and networks.

- A `Site` represents an information source with alternatives that may form product spaces.
- A `Channel` represents transformations between sites.
- A `Network` ties sites and channels together, forming directed acyclic graphs of information flow.

The framework is useful for modeling processes, systems, or any flow of information.
"""

from typing import List, Iterable, Callable, Union
from IPython.display import display, HTML

# Global unique index counter for generating IDs
_uix = 0
def _get_uix():
    """Generate and return a unique index."""
    global _uix
    _uix += 1
    return _uix

class _ST_Base:
    """
    Base class for socio-technical components.
    Provides common functionality for formatting and string representations.
    """
    def __format__(self, format_spec):
        return self.__str__().__format__(format_spec)

class Site(_ST_Base):
    """
    Represents an information source or grouping of sources within a network.

    Attributes:
        type (str): The type of this component ('s' for site).
        N (Network): The parent network this site belongs to.
        id (str): Unique identifier for the site within the network.
        label (str): Optional human-readable label for the site.
        _sites (dict): Subsites if this site is a group.
        _producer (Channel): The channel producing data for this site.
        _order (int): Computational order for dependency resolution.
    """

    def __init__(self, nw: "Network", *args):
        """
        Initialize a Site instance.

        Args:
            nw (Network): Parent network.
            *args: Additional arguments to define site or group of sites.
        """
        self.type = 's'
        self.N: "Network" = nw
        self.id = self.N._next_site_ix()
        self._sites = {}
        self._producer = None
        self._level = 4000

        if len(args) == 0:
            self.label = None
        elif len(args) == 1 and isinstance(args[0], str):
            self.label = args[0]
        elif all(isinstance(e, Site) for e in args):
            self._sites = {(a.id, a) for a in args}
        else:
            raise AttributeError("Invalid arguments for Site initialization.")

    def site(self, id):
        """Retrieve a subsite by id."""
        if id in self._sites:
            return self._sites[id]
        raise AttributeError(f"Site '{self.id}' does not contain the site '{id}'")

    def sites(self, *ids: List[str]):
        """Retrieve multiple subsites by their ids."""
        return [self.site(id) for id in ids]

    def _label(self):
        """Get the label of the site or its unique id if label is absent."""
        return self.label if self.label is not None else self.id

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return isinstance(other, Site) and self.__hash__() == other.__hash__()

    def __str__(self):
        return self._label()

    def __repr__(self):
        return f'{self._label()}'

    def __mul__(self, other):
        raise NotImplementedError("Multiplication is not implemented for Sites.")

class SiteQuery:
    """
    Query object for filtering and retrieving sites within a network.

    Attributes:
        sites (list[Site]): Initial list of sites to query.
        filters (list[callable]): List of filtering functions to apply.
    """

    def __init__(self, sites: Iterable[Site]):
        """
        Initialize a SiteQuery instance.

        Args:
            sites (Iterable[Site]): Collection of sites to query.
        """
        self.sites = list(sites)
        self.filters = []

    def label(self, labels: Union[str, List[str]]) -> 'SiteQuery':
        """Filter sites by label(s)."""
        if isinstance(labels, str):
            labels = [labels]
        self.filters.append(lambda site: site.label in labels)
        return self

    def type(self, site_type: str) -> 'SiteQuery':
        """Filter sites by type."""
        self.filters.append(lambda site: site.site_type == site_type)
        return self

    def __iter__(self):
        """Apply filters and iterate over matching sites."""
        filtered_sites = self.sites
        for filter_fn in self.filters:
            filtered_sites = filter(filter_fn, filtered_sites)
        return iter(filtered_sites)

    def __getitem__(self, index):
        """Retrieve filtered sites by index or slice."""
        filtered_sites = list(self.__iter__())
        return filtered_sites[index]

    def __len__(self):
        """Count the number of matching sites after filters."""
        return len(list(self.__iter__()))

    def __repr__(self):
        """Display the filtered collection of sites."""
        return repr(list(self.__iter__()))

    @property
    def ids(self) -> List[str]:
        """Get a list of IDs of the sites in the query."""
        return [site.id for site in self.__iter__()]

    @property
    def labels(self) -> List[str]:
        """Get a list of labels of the sites in the query."""
        return [site.label for site in self.__iter__()]

    @property
    def levels(self) -> List[tuple]:
        """Get a list of (level, site) tuples of the sites in the query, ordered by level."""
        return sorted(((site._level, site) for site in self.__iter__()), key=lambda x: x[0])

class Channel(_ST_Base):
    """
    Represents a connection between source and target sites in the network.

    Attributes:
        type (str): The type of this component ('c' for channel).
        N (Network): The parent network this channel belongs to.
        id (str): Unique identifier for the channel within the network.
        label (str): Optional human-readable label for the channel.
        _source (list[Site]): List of input sites.
        _target (set[Site]): Set of output sites.
        _order (int): Computational order for dependency resolution.
    """

    def __init__(self, nw: "Network", source, target, label=None):
        """
        Initialize a Channel instance.

        Args:
            nw (Network): Parent network.
            source (Site or list[Site]): Source sites providing inputs.
            target (Site or list[Site]): Target sites receiving outputs.
            label (str, optional): Label for the channel.
        """
        self.type = 'c'
        self.N: "Network" = nw
        self.id = self.N._next_channel_ix()
        self.label = self.id if label is None else label
        self._source = []
        self._target = set()

        self.add_input(source)
        self.add_output(target)
        self._level = -1

    def add_input(self, sites):
        """Add input sites to the channel."""
        if isinstance(sites, list):
            for s in sites:
                self.add_input(s)
        elif sites not in self._source:
            self._source.append(sites)
        return self

    def discard_input(self, sites):
        """Remove input sites from the channel."""
        if isinstance(sites, list):
            for s in sites:
                self.discard_input(s)
        else:
            self._source.remove(sites)
        return self

    def add_output(self, sites):
        """Add output sites to the channel."""
        if isinstance(sites, list):
            for s in sites:
                self.add_output(s)
        else:
            if sites._producer is None or sites._producer is self:
                sites._producer = self
                self._target.add(sites)
            else:
                raise Exception(f"A site can only be the output of one channel. Source of {sites} is {sites._producer}")
        return self

    def discard_output(self, sites):
        """Remove output sites from the channel."""
        if isinstance(sites, list):
            for s in sites:
                self.discard_output(s)
        else:
            if sites in self._target:
                sites._source = None
                self._target.discard(sites)
        return self

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return isinstance(other, Channel) and self.__hash__() == other.__hash__()

    def __str__(self):
        return f'{self.id}: {self._source} --> {self._target}'

    def __repr__(self):
        return f'<{self.label}: {self._source} --> {self._target}>'

    def tex2(self):
        arraysep = '\n'
        tikznode = '\\node '
        return f'''
    \[
    \\begin{{tikzpicture}}[node distance=1em, auto]
        % Define nodes
        \\node (lab) at (-4, 0) {{{self.id.replace('_', '')}}};
        \\node (mr) at (10, 0) {{}};
        \\node (ml) at (-5, 0) {{}};
        \\node (r) at (0, 0) {{}};
        \\node (l) at (3, 0) {{}};
            {arraysep.join([f'{tikznode} ({s.id.replace("_", "")}) [left=of r, yshift={0.5 + e - len(self._source) / 2.0}em] {{{s.__str__()}}};'
                            for (e, s) in enumerate(self._source)])}

            {arraysep.join([f'{tikznode} ({s.id.replace("_", "")}) [right=of l, yshift={0.5 + e - len(self._target) / 2.0}em] {{{s.__str__()}}};'
                            for (e, s) in enumerate(self._target)])}

        % Draw arrow
        \\draw[->] (r.east) -- (l.west) node[midway, above] {{\\textit{{{self.label}}}}};
    \end{{tikzpicture}}
    \]
    '''

    def plt(self):
        uix = _get_uix()

        html_content = f"""
        <div style="display: flex; align-items: center; justify-content: space-between; width: 100%; font-family: Arial; font-size: 16px;">
            <div style="text-align: right; align-items: right; margin-right: 12px; width: 30%">
                {''.join([f'<p>{s.__str__().replace("<", "&lt;").replace(">", "&gt;")}</p>' for s in self._source])}
            </div>
            <div style="text-align: center; position: relative; flex: 1;">
                <svg height="50" width="150" style="overflow: visible;">
                    <defs>
                        <marker id="arrowhead_{uix}" markerWidth="10" markerHeight="7" refX="10" refY="3.5" orient="auto">
                            <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" />
                        </marker>
                    </defs>
                    <line x1="0" y1="25" x2="150" y2="25" stroke="currentColor" stroke-width="2" marker-end="url(#arrowhead_{uix})" />
                </svg>
                <div style="position: absolute; top: 0; left: 50%; transform: translateX(-50%); font-size: 14px;">{self.label}</div>
            </div>
            <div style="text-align: left; margin-left: 12px;; width: 30%">
                {''.join([f'<p>{s.__str__().replace("<", "&lt;").replace(">", "&gt;")}</p>' for s in self._target])}
            </div>
        </div>
        """
        display(HTML(html_content))

class ChannelQuery:
    """
    Query object for filtering and retrieving channels within a network.

    Attributes:
        channels (list[Channel]): Initial list of channels to query.
        filters (list[callable]): List of filtering functions to apply.
    """

    def __init__(self, channels: Iterable[Channel]):
        """
        Initialize a ChannelQuery instance.

        Args:
            channels (Iterable[Channel]): Collection of channels to query.
        """
        self.channels = list(channels)
        self.filters = []

    def label(self, labels: Union[str, List[str]]) -> 'ChannelQuery':
        """Filter channels by label(s)."""
        if isinstance(labels, str):
            labels = [labels]
        self.filters.append(lambda channel: channel.label in labels)
        return self

    def source(self, source_sites: Union[Site, List[Site]]) -> 'ChannelQuery':
        """Filter channels by source site(s)."""
        if isinstance(source_sites, Site):
            source_sites = [source_sites]
        self.filters.append(lambda channel: any(site in channel._source for site in source_sites))
        return self

    def target(self, target_sites: Union[Site, List[Site]]) -> 'ChannelQuery':
        """Filter channels by target site(s)."""
        if isinstance(target_sites, Site):
            target_sites = [target_sites]
        self.filters.append(lambda channel: any(site in channel._target for site in target_sites))
        return self

    def __iter__(self):
        """Apply filters and iterate over matching channels."""
        filtered_channels = self.channels
        for filter_fn in self.filters:
            filtered_channels = filter(filter_fn, filtered_channels)
        return iter(filtered_channels)

    def __getitem__(self, index):
        """Retrieve filtered channels by index or slice."""
        filtered_channels = list(self.__iter__())
        return filtered_channels[index]

    def __len__(self):
        """Count the number of matching channels after filters."""
        return len(list(self.__iter__()))

    def __repr__(self):
        """Display the filtered collection of channels."""
        return repr(list(self.__iter__()))

    @property
    def ids(self) -> List[str]:
        """Get a list of IDs of the channels in the query."""
        return [channel.id for channel in self.__iter__()]

    @property
    def labels(self) -> List[str]:
        """Get a list of labels of the channels in the query."""
        return [channel.label for channel in self.__iter__()]

    @property
    def levels(self) -> List[tuple]:
        """Get a list of (level, channel) tuples of the channels in the query, ordered by level."""
        return sorted(((channel._level, channel) for channel in self.__iter__()), key=lambda x: x[0])

class Network:
    """
    Represents a collection of sites and channels, forming a directed acyclic graph.

    Attributes:
        _IMPLEMENTED_SPECS (tuple[str]): Supported specifications.
        _sites (dict): Dictionary of site objects.
        _channels (dict): Dictionary of channel objects.
        name (str): Name of the network.
        version (str): Version of the network.
    """

    _IMPLEMENTED_SPECS = ("IF0.1", "IF0.2")  # Supported specifications

    def __init__(self, spec="IF0.2", name=None, site_ids=None, channel_ids=None):
        """
        Initialize a Network instance.

        Args:
            spec (str): Specification version.
            name (str, optional): Name of the network.
            site_idss (list[str], optional): Ids of initial sites.
            channel_ids (list[str], optional): Ids of initial channels.
        """
        if spec not in self._IMPLEMENTED_SPECS:
            raise AttributeError(f'Unknown specification: {spec}. ')
        self._spec = spec
        self._sites = {}
        self._channels = {}
        self.name = name
        self.version = '0.0.1'
        self._site_ix = -1
        self._channel_ix = -1

        if site_ids is not None:
            tail = None
            for sn in site_ids:
                site = self.site(sn, create=True)
                if tail is not None:
                    c = self.channel(tail, site)
                    if channel_ids:
                        c.label = channel_ids.pop(0)
                tail = site

    def _next_site_ix(self):
        """Generate the next unique site index."""
        self._site_ix += 1
        return f'_s{self._site_ix}'

    def _next_channel_ix(self):
        """Generate the next unique channel index."""
        self._channel_ix += 1
        return f'_c{self._channel_ix}'

    def site(self, *args, create=False):
        """Retrieve or create a site."""
        if len(args) == 1 and isinstance(args[0], str):
            if args[0] in self._sites:
                return self._sites[args[0]]
            elif create:
                new = Site(self, *args)
                self._sites[new.id] = new
                return new
            else:
                raise KeyError(f'Key {args[0]} is not a recognized site.')

    def sites(self, *ids:list[str], create=False):
        """Retrieve or create a sites through a site-query."""
        if len(ids) == 0:
            return SiteQuery(self._sites.values())
        else:
            return SiteQuery([self.site(id, create=create) for id in ids])

    def channel(self, *args, id=None):
        """Create a new channel between source and target."""
        if len(args) == 1 and isinstance(args[0], str):
            if args[0] in self._channels:
                return self._channels[args[0]]
            else:
                raise KeyError(f'Key {args[0]} is not a recognized channel.')

        # some kind of create call
        elif len(args) == 2:
            new = Channel(self, *args)
            self._channels[new.id] = new
            return new

    def channels(self, *ids:list[str]):
        """Retrieve channels through a channel-query."""
        if len(ids) == 0:
            return ChannelQuery(self._channels.values())
        else:
            return ChannelQuery([self.channel(id) for id in ids])

    def compute_order(self):
        """Compute and assign the execution order of sites and channels."""

        # reset order
        for s in self._sites.values():
            if s._producer is None:
                s._level = -1
            else:
                s._level = 1000

        for c in self._channels.values():
            c._level = 1000
            for s in c._source: s._level = 0 if s._level == -1 else s._level

        # compute order of sites and channels
        done = False
        i = 0
        while not done and i < (len(self._channels)+10):
            done = True
            for c in self._channels.values():
                if c._level < i: continue
                skip = False
                for s in c._source:
                    if s._level > i:
                        skip = True
                        break
                if skip: continue

                done = False
                c._level = i
                for s in c._target:
                    s._level = i + 1
            i += 1

        # Done. Sort in structure order.

        self._channels = dict(sorted(self._channels.items(), key=lambda x: x[1]._level))
        for c in self._channels.values():
            c._source = sorted(c._source, key=lambda x: -x._level)

        # Evaluate the result

        if i > len(self._channels) + 1:
            print(f'Warning: failed to compute network structure.')

        if any(s._level == -1 for s in self._sites.values()):
            print(f'Warning: There are orphaned sites. {[s for s in self._sites.values() if s._level == -1]}')

        if any(c._level == 1000 for c in self._channels.values()):
            print(f'Warning: There are unreachable channels.  {[c for c in self._channels.values() if c._level == 1000]}')

    def plt(self):
        for channel in self._channels.values():
            channel.plt()

    def tex(self):
        return '\n'.join([f'%{channel.__str__()}\n{channel.tex2()}' for channel in self._channels.values()])
