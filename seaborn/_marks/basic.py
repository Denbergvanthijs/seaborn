from __future__ import annotations
import numpy as np
import matplotlib as mpl
from matplotlib.colors import to_rgba

from seaborn._compat import MarkerStyle
from seaborn._marks.base import Mark, Feature


class Point(Mark):  # TODO types

    supports = ["color"]

    def __init__(
        self,
        color=Feature("C0"),
        edgecolor=Feature("w"),
        alpha=Feature(1),  # TODO auto alpha?
        marker=Feature(rc="scatter.marker"),
        pointsize=Feature(5),
        linewidth=Feature(1),  # TODO how to scale with point size?
        edgewidth=Feature(.25),  # TODO how to scale with point size?
        fill=Feature(True),
        jitter=None,
        **kwargs,  # TODO needed?
    ):

        super().__init__(**kwargs)

        # TODO do this automatically using self.supports?
        self.features = dict(
            color=color,
            edgecolor=edgecolor,
            alpha=alpha,
            marker=marker,
            pointsize=pointsize,
            linewidth=linewidth,
            edgewidth=edgewidth,
            fill=fill,
        )

        self.jitter = jitter  # TODO decide on form of jitter and add type hinting

    def _adjust(self, df, orient):

        if self.jitter is None:
            return df

        x, y = self.jitter  # TODO maybe not format, and do better error handling

        # TODO maybe accept a Jitter class so we can control things like distribution?
        # If we do that, should we allow convenient flexibility (i.e. (x, y) tuple)
        # in the object interface, or be simpler but more verbose?

        # TODO note that some marks will have multiple adjustments
        # (e.g. strip plot has both dodging and jittering)

        # TODO native scale of jitter? maybe just for a Strip subclass?

        rng = np.random.default_rng()  # TODO seed?

        n = len(df)
        x_jitter = 0 if not x else rng.uniform(-x, +x, n)
        y_jitter = 0 if not y else rng.uniform(-y, +y, n)

        # TODO: this fails if x or y are paired. Apply to all columns that start with y?
        return df.assign(x=df["x"] + x_jitter, y=df["y"] + y_jitter)

    def _plot_split(self, keys, data, ax, orient, kws):

        # TODO can we simplify this by modifying data with mappings before sending in?
        # Likewise, will we need to know `keys` here? Elsewhere we do `if key in keys`,
        # but I think we can (or can make it so we can) just do `if key in data`.

        # Then the signature could be _plot_split(ax, data, kws):  ... much simpler!

        # TODO Not backcompat with allowed (but nonfunctional) univariate plots

        kws = kws.copy()

        color = self._resolve("color", data, to_rgba)
        edgecolor = self._resolve("edgecolor", data, to_rgba)
        alpha = self._resolve("alpha", data, float)

        marker = self._resolve("marker", data, MarkerStyle)
        fill = self._resolve("fill", data, bool)
        pointsize = self._resolve("pointsize", data, float)

        # TODO matplotlib has "edgecolor='face'" and it would be good to keep that
        # But it would be BETTER to have succient way of specifiying, e.g.
        # edgecolor = set_hls_values(facecolor, l=.8)

        # TODO lots of questions about the best way to implement fill
        # e.g. we need to remap color to edgecolor where fill is false
        color[:, 3] = alpha

        fill &= np.array([m.is_filled() for m in marker])
        edgecolor[~fill] = color[~fill]
        color[~fill, 3] = 0

        paths = [m.get_path().transformed(m.get_transform()) for m in marker]

        points = mpl.collections.PathCollection(
            paths,
            sizes=pointsize ** 2,
            offsets=data[["x", "y"]].to_numpy(),
            facecolors=color,
            edgecolors=edgecolor,
            transOffset=ax.transData,
            transform=mpl.transforms.IdentityTransform(),
        )
        ax.add_collection(points)
        ax.autoscale_view()


class Line(Mark):

    # TODO how to handle distinction between stat groupers and plot groupers?
    # i.e. Line needs to aggregate by x, but not plot by it
    # also how will this get parametrized to support orient=?
    # TODO will this sort by the orient dimension like lineplot currently does?
    grouping_vars = ["color", "marker", "linestyle", "linewidth"]
    supports = ["color", "marker", "linestyle", "linewidth"]

    def _plot_split(self, keys, data, ax, orient, kws):

        if "color" in keys:
            kws["color"] = self.mappings["color"](keys["color"])
        if "linestyle" in keys:
            kws["linestyle"] = self.mappings["linestyle"](keys["linestyle"])
        if "linewidth" in keys:
            kws["linewidth"] = self.mappings["linewidth"](keys["linewidth"])

        ax.plot(data["x"], data["y"], **kws)


class Area(Mark):

    grouping_vars = ["color"]
    supports = ["color"]

    def _plot_split(self, keys, data, ax, orient, kws):

        if "color" in keys:
            # TODO as we need the kwarg to be facecolor, that should be the mappable?
            kws["facecolor"] = self.mappings["color"](keys["color"])

        # TODO how will orient work here?
        # Currently this requires you to specify both orient and use y, xmin, xmin
        # to get a fill along the x axis. Seems like we should need only one of those?
        # Alternatively, should we just make the PolyCollection manually?
        if orient == "x":
            ax.fill_between(data["x"], data["ymin"], data["ymax"], **kws)
        else:
            ax.fill_betweenx(data["y"], data["xmin"], data["xmax"], **kws)
