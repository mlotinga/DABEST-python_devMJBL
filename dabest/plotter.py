#!/usr/bin/python
# -*-coding: utf-8 -*-
# Author: Joses Ho
# Email : joseshowh@gmail.com


def EffectSizeDataFramePlotter(EffectSizeDataFrame, **plot_kwargs):
    """
    Custom function that creates an estimation plot from an EffectSizeDataFrame.
    Keywords
    --------
    EffectSizeDataFrame: A `dabest` EffectSizeDataFrame object.
    **plot_kwargs:
        color_col=None
        raw_marker_size=6, es_marker_size=9,
        swarm_label=None, contrast_label=None, delta2_label=None,
        swarm_ylim=None, contrast_ylim=None, delta2_ylim=None,
        custom_palette=None, swarm_desat=0.5, halfviolin_desat=1,
        halfviolin_alpha=0.8,
        face_color = None,
        bar_label=None, bar_desat=0.8, bar_width = 0.5,bar_ylim = None,
        ci=None, ci_type='bca', err_color=None,
        float_contrast=True,
        show_pairs=True,
        show_delta2=True,
        group_summaries=None,
        group_summaries_offset=0.1,
        fig_size=None,
        dpi=100,
        ax=None,
        swarmplot_kwargs=None,
        violinplot_kwargs=None,
        slopegraph_kwargs=None,
        sankey_kwargs=None,
        reflines_kwargs=None,
        group_summary_kwargs=None,
        legend_kwargs=None,
    """

    import numpy as np
    import seaborn as sns
    import matplotlib.pyplot as plt
    import pandas as pd

    from .misc_tools import merge_two_dicts
    from .plot_tools import halfviolin, get_swarm_spans, gapped_lines, proportion_error_bar, sankeydiag
    from ._stats_tools.effsize import _compute_standardizers, _compute_hedges_correction_factor

    import logging
    # Have to disable logging of warning when get_legend_handles_labels()
    # tries to get from slopegraph.
    logging.disable(logging.WARNING)

    # Save rcParams that I will alter, so I can reset back.
    original_rcParams = {}
    _changed_rcParams = ['axes.grid']
    for parameter in _changed_rcParams:
        original_rcParams[parameter] = plt.rcParams[parameter]

    plt.rcParams['axes.grid'] = False

    ytick_color = plt.rcParams["ytick.color"]
    face_color = plot_kwargs["face_color"]
    if plot_kwargs["face_color"] is None:
        face_color = "white"

    dabest_obj  = EffectSizeDataFrame.dabest_obj
    plot_data   = EffectSizeDataFrame._plot_data
    xvar        = EffectSizeDataFrame.xvar
    yvar        = EffectSizeDataFrame.yvar
    is_paired   = EffectSizeDataFrame.is_paired
    delta2      = EffectSizeDataFrame.delta2
    mini_meta   = EffectSizeDataFrame.mini_meta
    effect_size = EffectSizeDataFrame.effect_size
    proportional = EffectSizeDataFrame.proportional

    all_plot_groups = dabest_obj._all_plot_groups
    idx             = dabest_obj.idx

    if effect_size != "mean_diff" or not delta2:
        show_delta2 = False
    else:
        show_delta2 = plot_kwargs["show_delta2"]

    if effect_size != "mean_diff" or not mini_meta:
        show_mini_meta = False
    else:
        show_mini_meta = plot_kwargs["show_mini_meta"]

    if show_delta2 and show_mini_meta:
        err0 = "`show_delta2` and `show_mini_meta` cannot be True at the same time."
        raise ValueError(err0)

    # Disable Gardner-Altman plotting if any of the idxs comprise of more than
    # two groups or if it is a delta-delta plot.
    float_contrast   = plot_kwargs["float_contrast"]
    effect_size_type = EffectSizeDataFrame.effect_size
    if len(idx) > 1 or len(idx[0]) > 2:
        float_contrast = False

    if effect_size_type in ['cliffs_delta']:
        float_contrast = False

    if show_delta2 or show_mini_meta:
        float_contrast = False  

    if not is_paired:
        show_pairs = False
    else:
        show_pairs = plot_kwargs["show_pairs"]

    # Set default kwargs first, then merge with user-dictated ones.
    default_swarmplot_kwargs = {'size': plot_kwargs["raw_marker_size"]}
    if plot_kwargs["swarmplot_kwargs"] is None:
        swarmplot_kwargs = default_swarmplot_kwargs
    else:
        swarmplot_kwargs = merge_two_dicts(default_swarmplot_kwargs,
                                           plot_kwargs["swarmplot_kwargs"])

    # Barplot kwargs
    default_barplot_kwargs = {"estimator": np.mean, "ci": plot_kwargs["ci"]}

    if plot_kwargs["barplot_kwargs"] is None:
        barplot_kwargs = default_barplot_kwargs
    else:
        barplot_kwargs = merge_two_dicts(default_barplot_kwargs,
                                         plot_kwargs["barplot_kwargs"])

    # Sankey Diagram kwargs
    default_sankey_kwargs = {"width": 0.4, "align": "center",
                            "alpha": 0.4, "rightColor": False,
                            "bar_width":0.2}
    if plot_kwargs["sankey_kwargs"] is None:
        sankey_kwargs = default_sankey_kwargs
    else:
        sankey_kwargs = merge_two_dicts(default_sankey_kwargs,
                                        plot_kwargs["sankey_kwargs"])
                

    # Violinplot kwargs.
    default_violinplot_kwargs = {'widths':0.5, 'vert':True,
                               'showextrema':False, 'showmedians':False}
    if plot_kwargs["violinplot_kwargs"] is None:
        violinplot_kwargs = default_violinplot_kwargs
    else:
        violinplot_kwargs = merge_two_dicts(default_violinplot_kwargs,
                                            plot_kwargs["violinplot_kwargs"])

    # slopegraph kwargs.
    default_slopegraph_kwargs = {'lw':1, 'alpha':0.5}
    if plot_kwargs["slopegraph_kwargs"] is None:
        slopegraph_kwargs = default_slopegraph_kwargs
    else:
        slopegraph_kwargs = merge_two_dicts(default_slopegraph_kwargs,
                                            plot_kwargs["slopegraph_kwargs"])

    # Zero reference-line kwargs.
    default_reflines_kwargs = {'linestyle':'solid', 'linewidth':0.75,
                                'zorder': 2,
                                'color': ytick_color}
    if plot_kwargs["reflines_kwargs"] is None:
        reflines_kwargs = default_reflines_kwargs
    else:
        reflines_kwargs = merge_two_dicts(default_reflines_kwargs,
                                          plot_kwargs["reflines_kwargs"])

    # Legend kwargs.
    default_legend_kwargs = {'loc': 'upper left', 'frameon': False}
    if plot_kwargs["legend_kwargs"] is None:
        legend_kwargs = default_legend_kwargs
    else:
        legend_kwargs = merge_two_dicts(default_legend_kwargs,
                                        plot_kwargs["legend_kwargs"])

    # Group summaries kwargs.
    gs_default = {'mean_sd', 'median_quartiles', None}
    if plot_kwargs["group_summaries"] not in gs_default:
        raise ValueError('group_summaries must be one of'
        ' these: {}.'.format(gs_default) )

    default_group_summary_kwargs = {'zorder': 3, 'lw': 2,
                                    'alpha': 1}
    if plot_kwargs["group_summary_kwargs"] is None:
        group_summary_kwargs = default_group_summary_kwargs
    else:
        group_summary_kwargs = merge_two_dicts(default_group_summary_kwargs,
                                               plot_kwargs["group_summary_kwargs"])

    # Create color palette that will be shared across subplots.
    color_col = plot_kwargs["color_col"]
    if color_col is None:
        color_groups = pd.unique(plot_data[xvar])
        bootstraps_color_by_group = True
    else:
        if color_col not in plot_data.columns:
            raise KeyError("``{}`` is not a column in the data.".format(color_col))
        color_groups = pd.unique(plot_data[color_col])
        bootstraps_color_by_group = False
    if show_pairs:
        bootstraps_color_by_group = False

    # Handle the color palette.
    names = color_groups
    n_groups = len(color_groups)
    custom_pal = plot_kwargs["custom_palette"]
    swarm_desat = plot_kwargs["swarm_desat"]
    bar_desat = plot_kwargs["bar_desat"]
    contrast_desat = plot_kwargs["halfviolin_desat"]

    if custom_pal is None:
        unsat_colors = sns.color_palette(n_colors=n_groups)
    else:

        if isinstance(custom_pal, dict):
            groups_in_palette = {k: v for k,v in custom_pal.items()
                                 if k in color_groups}

            # # check that all the keys in custom_pal are found in the
            # # color column.
            # col_grps = {k for k in color_groups}
            # pal_grps = {k for k in custom_pal.keys()}
            # not_in_pal = pal_grps.difference(col_grps)
            # if len(not_in_pal) > 0:
            #     err1 = 'The custom palette keys {} '.format(not_in_pal)
            #     err2 = 'are not found in `{}`. Please check.'.format(color_col)
            #     errstring = (err1 + err2)
            #     raise IndexError(errstring)

            names = groups_in_palette.keys()
            unsat_colors = groups_in_palette.values()

        elif isinstance(custom_pal, list):
            unsat_colors = custom_pal[0: n_groups]

        elif isinstance(custom_pal, str):
            # check it is in the list of matplotlib palettes.
            if custom_pal in plt.colormaps():
                unsat_colors = sns.color_palette(custom_pal, n_groups)
            else:
                err1 = 'The specified `custom_palette` {}'.format(custom_pal)
                err2 = ' is not a matplotlib palette. Please check.'
                raise ValueError(err1 + err2)

    if custom_pal is None and color_col is None:
        swarm_colors = [sns.desaturate(c, swarm_desat) for c in unsat_colors]
        plot_palette_raw = dict(zip(names.categories, swarm_colors))

        bar_color = [sns.desaturate(c, bar_desat) for c in unsat_colors]
        plot_palette_bar = dict(zip(names.categories, bar_color))

        contrast_colors = [sns.desaturate(c, contrast_desat) for c in unsat_colors]
        plot_palette_contrast = dict(zip(names.categories, contrast_colors))

        # For Sankey Diagram plot, no need to worry about the color, each bar will have the same two colors
        # default color palette will be set to "hls"
        plot_palette_sankey = None

    else:
        swarm_colors = [sns.desaturate(c, swarm_desat) for c in unsat_colors]
        plot_palette_raw = dict(zip(names, swarm_colors))

        bar_color = [sns.desaturate(c, bar_desat) for c in unsat_colors]
        plot_palette_bar = dict(zip(names, bar_color))

        contrast_colors = [sns.desaturate(c, contrast_desat) for c in unsat_colors]
        plot_palette_contrast = dict(zip(names, contrast_colors))

        plot_palette_sankey = custom_pal

    # Infer the figsize.
    fig_size   = plot_kwargs["fig_size"]
    if fig_size is None:
        all_groups_count = np.sum([len(i) for i in dabest_obj.idx])
        # Increase the width for delta-delta graph
        if show_delta2 or show_mini_meta:
            all_groups_count += 2
        if is_paired and show_pairs is True and proportional is False:
            frac = 0.75
        else:
            frac = 1
        if float_contrast is True:
            height_inches = 4
            each_group_width_inches = 2.5 * frac
        else:
            height_inches = 6
            each_group_width_inches = 1.5 * frac

        width_inches = (each_group_width_inches * all_groups_count)
        fig_size = (width_inches, height_inches)

    # Initialise the figure.
    # sns.set(context="talk", style='ticks')
    init_fig_kwargs = dict(figsize=fig_size, dpi=plot_kwargs["dpi"]
                            ,tight_layout=True)

    width_ratios_ga = [2.5, 1]
    h_space_cummings = 0.3
    if plot_kwargs["ax"] is not None:
        # New in v0.2.6.
        # Use inset axes to create the estimation plot inside a single axes.
        # Author: Adam L Nekimken. (PR #73)
        inset_contrast = True
        rawdata_axes = plot_kwargs["ax"]
        ax_position = rawdata_axes.get_position()  # [[x0, y0], [x1, y1]]
        
        fig = rawdata_axes.get_figure()
        fig.patch.set_facecolor(face_color)
        
        if float_contrast is True:
            axins = rawdata_axes.inset_axes(
                    [1, 0,
                     width_ratios_ga[1]/width_ratios_ga[0], 1])
            rawdata_axes.set_position(  # [l, b, w, h]
                    [ax_position.x0,
                     ax_position.y0,
                     (ax_position.x1 - ax_position.x0) * (width_ratios_ga[0] /
                                                         sum(width_ratios_ga)),
                     (ax_position.y1 - ax_position.y0)])

            contrast_axes = axins

        else:
            axins = rawdata_axes.inset_axes([0, -1 - h_space_cummings, 1, 1])
            plot_height = ((ax_position.y1 - ax_position.y0) /
                           (2 + h_space_cummings))
            rawdata_axes.set_position(
                    [ax_position.x0,
                     ax_position.y0 + (1 + h_space_cummings) * plot_height,
                     (ax_position.x1 - ax_position.x0),
                     plot_height])

            # If the contrast axes are NOT floating, create lists to store
            # raw ylims and raw tick intervals, so that I can normalize
            # their ylims later.
            contrast_ax_ylim_low = list()
            contrast_ax_ylim_high = list()
            contrast_ax_ylim_tickintervals = list()
        contrast_axes = axins
        rawdata_axes.contrast_axes = axins

    else:
        inset_contrast = False
        # Here, we hardcode some figure parameters.
        if float_contrast is True:
            fig, axx = plt.subplots(
                    ncols=2,
                    gridspec_kw={"width_ratios": width_ratios_ga,
                                 "wspace": 0},
                                 **init_fig_kwargs)
            fig.patch.set_facecolor(face_color)

        else:
            fig, axx = plt.subplots(nrows=2,
                                    gridspec_kw={"hspace": 0.3},
                                    **init_fig_kwargs)
            fig.patch.set_facecolor(face_color)
            # If the contrast axes are NOT floating, create lists to store
            # raw ylims and raw tick intervals, so that I can normalize
            # their ylims later.
            contrast_ax_ylim_low = list()
            contrast_ax_ylim_high = list()
            contrast_ax_ylim_tickintervals = list()

        rawdata_axes  = axx[0]
        contrast_axes = axx[1]
    rawdata_axes.set_frame_on(False)
    contrast_axes.set_frame_on(False)
    # fig.set_tight_layout(False)

    redraw_axes_kwargs = {'colors'     : ytick_color,
                          'facecolors' : ytick_color,
                          'lw'      : 1,
                          'zorder'  : 10,
                          'clip_on' : False}

    swarm_ylim = plot_kwargs["swarm_ylim"]

    if swarm_ylim is not None:
        rawdata_axes.set_ylim(swarm_ylim)

    one_sankey = None
    if is_paired is not None:
        one_sankey = False # Flag to indicate if only one sankey is plotted.

    if show_pairs is True:
        if is_paired == "baseline":
            temp_idx = []
            for i in idx:
                control = i[0]
                temp_idx.extend(((control, test) for test in i[1:]))
            temp_idx = tuple(temp_idx)

            temp_all_plot_groups = []
            for i in temp_idx:
                temp_all_plot_groups.extend(list(i))
        else:
            temp_idx = []
            for i in idx:
                for j in range(len(i)-1):
                    control = i[j]
                    test = i[j+1]
                    temp_idx.append((control, test))
            temp_all_plot_groups = []
            for i in temp_idx:
                temp_all_plot_groups.extend(list(i))
        if proportional==False:
            temp_idx = idx
            temp_all_plot_groups = all_plot_groups
        # Plot the raw data as a slopegraph.
        # Pivot the long (melted) data.
            if color_col is None:
                pivot_values = yvar
            else:
                pivot_values = [yvar, color_col]
            pivoted_plot_data = pd.pivot(data=plot_data, index=dabest_obj.id_col,
                                         columns=xvar, values=pivot_values)
            x_start = 0
            for ii, current_tuple in enumerate(temp_idx):
                if len(temp_idx) > 1:
                    # Select only the data for the current tuple.
                    if color_col is None:
                        current_pair = pivoted_plot_data.reindex(columns=current_tuple)
                    else:
                        current_pair = pivoted_plot_data[yvar].reindex(columns=current_tuple)
                else:
                    if color_col is None:
                        current_pair = pivoted_plot_data
                    else:
                        current_pair = pivoted_plot_data[yvar]
                grp_count = len(current_tuple)
                # Iterate through the data for the current tuple.
                for ID, observation in current_pair.iterrows():
                    x_points = [t for t in range(x_start, x_start + grp_count)]
                    y_points = observation.tolist()

                    if color_col is None:
                        slopegraph_kwargs['color'] = ytick_color
                    else:
                        color_key = pivoted_plot_data[color_col,
                                                      current_tuple[0]].loc[ID]
                        if isinstance(color_key, str) == True:
                            slopegraph_kwargs['color'] = plot_palette_raw[color_key]
                            slopegraph_kwargs['label'] = color_key

                    rawdata_axes.plot(x_points, y_points, **slopegraph_kwargs)
                x_start = x_start + grp_count
            # Set the tick labels, because the slopegraph plotting doesn't.
            rawdata_axes.set_xticks(np.arange(0, len(temp_all_plot_groups)))
            rawdata_axes.set_xticklabels(temp_all_plot_groups)
        else:
            # Plot the raw data as a set of Sankey Diagrams aligned like barplot.

            group_summaries = plot_kwargs["group_summaries"]
            if group_summaries is None:
                group_summaries = "mean_sd"
            err_color = plot_kwargs["err_color"]
            if err_color == None:
                err_color = "black"

            if show_pairs is True:
                sankey_control_group = []
                sankey_test_group = []
                for i in temp_idx:
                    sankey_control_group.append(i[0])
                    sankey_test_group.append(i[1])                   

            if len(temp_all_plot_groups) == 2:
                one_sankey = True   
            
            # Replace the paired proportional plot with sankey diagram
            sankey = sankeydiag(plot_data, xvar=xvar, yvar=yvar, 
                            left_idx=sankey_control_group, 
                            right_idx=sankey_test_group,
                            palette=plot_palette_sankey,
                            ax=rawdata_axes, 
                            one_sankey=one_sankey,
                            **sankey_kwargs)
                            
    else:
        if proportional==False:
            # Plot the raw data as a swarmplot.
            rawdata_plot = sns.swarmplot(data=plot_data, x=xvar, y=yvar,
                                         ax=rawdata_axes,
                                         order=all_plot_groups, hue=color_col,
                                         palette=plot_palette_raw, zorder=1,
                                         **swarmplot_kwargs)
        else:
            # Plot the raw data as a barplot.
            bar1_df = pd.DataFrame({xvar: all_plot_groups, 'proportion': np.ones(len(all_plot_groups))})
            bar1 = sns.barplot(data=bar1_df, x=xvar, y="proportion",
                               ax=rawdata_axes,
                               order=all_plot_groups,
                               linewidth=2, facecolor=(1, 1, 1, 0), edgecolor=bar_color,
                               zorder=1)
            bar2 = sns.barplot(data=plot_data, x=xvar, y=yvar,
                               ax=rawdata_axes,
                               order=all_plot_groups,
                               palette=plot_palette_bar,
                               zorder=1,
                               **barplot_kwargs)
            # adjust the width of bars
            bar_width = plot_kwargs["bar_width"]
            for bar in bar1.patches:
                x = bar.get_x()
                width = bar.get_width()
                centre = x + width / 2.
                bar.set_x(centre - bar_width / 2.)
                bar.set_width(bar_width)

        # Plot the gapped line summaries, if this is not a Cumming plot.
        # Also, we will not plot gapped lines for paired plots. For now.
        group_summaries = plot_kwargs["group_summaries"]
        if group_summaries is None:
            group_summaries = "mean_sd"

        if group_summaries is not None and proportional==False:
            # Create list to gather xspans.
            xspans = []
            line_colors = []
            for jj, c in enumerate(rawdata_axes.collections):
                try:
                    _, x_max, _, _ = get_swarm_spans(c)
                    x_max_span = x_max - jj
                    xspans.append(x_max_span)
                except TypeError:
                    # we have got a None, so skip and move on.
                    pass

                if bootstraps_color_by_group is True:
                    line_colors.append(plot_palette_raw[all_plot_groups[jj]])

            if len(line_colors) != len(all_plot_groups):
                line_colors = ytick_color

            gapped_lines(plot_data, x=xvar, y=yvar,
                         # Hardcoded offset...
                         offset=xspans + np.array(plot_kwargs["group_summaries_offset"]),
                         line_color=line_colors,
                         gap_width_percent=1.5,
                         type=group_summaries, ax=rawdata_axes,
                         **group_summary_kwargs)

        if group_summaries is not None and proportional == True:

            err_color = plot_kwargs["err_color"]
            if err_color == None:
                err_color = "black"
            proportion_error_bar(plot_data, x=xvar, y=yvar,
                         offset=0,
                         line_color=err_color,
                         gap_width_percent=1.5,
                         type=group_summaries, ax=rawdata_axes,
                         **group_summary_kwargs)

    # Add the counts to the rawdata axes xticks.
    counts = plot_data.groupby(xvar).count()[yvar]
    ticks_with_counts = []
    for xticklab in rawdata_axes.xaxis.get_ticklabels():
        t = xticklab.get_text()
        if t.rfind("\n") != -1:
            te = t[t.rfind("\n") + len("\n"):]
            N = str(counts.loc[te])
            te = t
        else:
            te = t
            N = str(counts.loc[te])

        ticks_with_counts.append("{}\nN = {}".format(te, N))

    rawdata_axes.set_xticklabels(ticks_with_counts)

    # Save the handles and labels for the legend.
    handles, labels = rawdata_axes.get_legend_handles_labels()
    legend_labels  = [l for l in labels]
    legend_handles = [h for h in handles]
    if bootstraps_color_by_group is False:
        rawdata_axes.legend().set_visible(False)

    # Enforce the xtick of rawdata_axes to be 0 and 1 after drawing only one sankey
    if one_sankey:
        rawdata_axes.set_xticks([0, 1])

    # Plot effect sizes and bootstraps.
    # Take note of where the `control` groups are.
    if is_paired == "baseline" and show_pairs == True:
        if proportional == True and one_sankey == False:
            ticks_to_skip = []
            ticks_to_plot = np.arange(0, len(temp_all_plot_groups)/2).tolist()
            ticks_to_start_sankey = np.cumsum([len(i)-1 for i in idx]).tolist()
            ticks_to_start_sankey.pop()
            ticks_to_start_sankey.insert(0, 0)
        else:
            ticks_to_skip = np.arange(0, len(temp_all_plot_groups), 2).tolist()
            ticks_to_plot = np.arange(1, len(temp_all_plot_groups), 2).tolist()
            ticks_to_skip_contrast = np.cumsum([(len(t)-1)*2 for t in idx])[:-1].tolist()
            ticks_to_skip_contrast.insert(0, 0)
    else:
        if proportional == True and one_sankey == False:
            ticks_to_skip = [len(sankey_control_group)]
            # Then obtain the ticks where we have to plot the effect sizes.
            ticks_to_plot = [t for t in range(0, len(temp_idx))
                        if t not in ticks_to_skip]
            ticks_to_skip = []
            ticks_to_start_sankey = np.cumsum([len(i)-1 for i in idx]).tolist()
            ticks_to_start_sankey.pop()
            ticks_to_start_sankey.insert(0, 0)
        else:
            ticks_to_skip = np.cumsum([len(t) for t in idx])[:-1].tolist()
            ticks_to_skip.insert(0, 0)
            # Then obtain the ticks where we have to plot the effect sizes.
            ticks_to_plot = [t for t in range(0, len(all_plot_groups))
                        if t not in ticks_to_skip]

    # Plot the bootstraps, then the effect sizes and CIs.
    es_marker_size   = plot_kwargs["es_marker_size"]
    halfviolin_alpha = plot_kwargs["halfviolin_alpha"]

    ci_type = plot_kwargs["ci_type"]

    results      = EffectSizeDataFrame.results
    contrast_xtick_labels = []


    for j, tick in enumerate(ticks_to_plot):
        current_group     = results.test[j]
        current_control   = results.control[j]
        current_bootstrap = results.bootstraps[j]
        current_effsize   = results.difference[j]
        if ci_type == "bca":
            current_ci_low    = results.bca_low[j]
            current_ci_high   = results.bca_high[j]
        else:
            current_ci_low    = results.pct_low[j]
            current_ci_high   = results.pct_high[j]


        # Create the violinplot.
        # New in v0.2.6: drop negative infinities before plotting.
        v = contrast_axes.violinplot(current_bootstrap[~np.isinf(current_bootstrap)],
                                     positions=[tick],
                                     **violinplot_kwargs)
        # Turn the violinplot into half, and color it the same as the swarmplot.
        # Do this only if the color column is not specified.
        # Ideally, the alpha (transparency) fo the violin plot should be
        # less than one so the effect size and CIs are visible.
        if bootstraps_color_by_group is True:
            fc = plot_palette_contrast[current_group]
        else:
            fc = "grey"

        halfviolin(v, fill_color=fc, alpha=halfviolin_alpha)

        # Plot the effect size.
        contrast_axes.plot([tick], current_effsize, marker='o',
                           color=ytick_color,
                           markersize=es_marker_size)
        # Plot the confidence interval.
        contrast_axes.plot([tick, tick],
                           [current_ci_low, current_ci_high],
                           linestyle="-",
                           color=ytick_color,
                           linewidth=group_summary_kwargs['lw'])

        contrast_xtick_labels.append("{}\nminus\n{}".format(current_group,
                                                   current_control))

    # Plot mini-meta violin
    if show_mini_meta or show_delta2:
        if show_mini_meta:
            mini_meta_delta = EffectSizeDataFrame.mini_meta_delta
            data            = mini_meta_delta.bootstraps_weighted_delta
            difference      = mini_meta_delta.difference
            if ci_type == "bca":
                ci_low          = mini_meta_delta.bca_low
                ci_high         = mini_meta_delta.bca_high
            else:
                ci_low          = mini_meta_delta.pct_low
                ci_high         = mini_meta_delta.pct_high
        else: 
            delta_delta     = EffectSizeDataFrame.delta_delta
            data            = delta_delta.bootstraps_delta_delta
            difference      = delta_delta.difference
            if ci_type == "bca":
                ci_low          = delta_delta.bca_low
                ci_high         = delta_delta.bca_high
            else:
                ci_low          = delta_delta.pct_low
                ci_high         = delta_delta.pct_high
        #Create the violinplot.
        #New in v0.2.6: drop negative infinities before plotting.
        position = max(rawdata_axes.get_xticks())+2
        v = contrast_axes.violinplot(data[~np.isinf(data)],
                                     positions=[position],
                                     **violinplot_kwargs)

        fc = "grey"

        halfviolin(v, fill_color=fc, alpha=halfviolin_alpha)

        # Plot the effect size.
        contrast_axes.plot([position], difference, marker='o',
                           color=ytick_color,
                           markersize=es_marker_size)
        # Plot the confidence interval.
        contrast_axes.plot([position, position],
                           [ci_low, ci_high],
                           linestyle="-",
                           color=ytick_color,
                           linewidth=group_summary_kwargs['lw'])
        if show_mini_meta:
            contrast_xtick_labels.extend(["","Weighted delta"])
        else:
            contrast_xtick_labels.extend(["","delta-delta"])

    # Make sure the contrast_axes x-lims match the rawdata_axes xlims,
    # and add an extra violinplot tick for delta-delta plot.
    if show_delta2 is False and show_mini_meta is False:
        contrast_axes.set_xticks(rawdata_axes.get_xticks())
    else:
        temp = rawdata_axes.get_xticks()
        temp = np.append(temp, [max(temp)+1, max(temp)+2])
        contrast_axes.set_xticks(temp)

    if show_pairs is True:
        max_x = contrast_axes.get_xlim()[1]
        rawdata_axes.set_xlim(-0.375, max_x)

    if float_contrast is True:
        contrast_axes.set_xlim(0.5, 1.5)
    elif show_delta2 or show_mini_meta:
        # Increase the xlim of raw data by 2
        temp = rawdata_axes.get_xlim()
        if show_pairs:
            rawdata_axes.set_xlim(temp[0], temp[1]+0.25)
        else:
            rawdata_axes.set_xlim(temp[0], temp[1]+2)
        contrast_axes.set_xlim(rawdata_axes.get_xlim())
    else:
        contrast_axes.set_xlim(rawdata_axes.get_xlim())

    # Properly label the contrast ticks.
    for t in ticks_to_skip:
        contrast_xtick_labels.insert(t, "")
    
    contrast_axes.set_xticklabels(contrast_xtick_labels)

    if bootstraps_color_by_group is False:
        legend_labels_unique = np.unique(legend_labels)
        unique_idx = np.unique(legend_labels, return_index=True)[1]
        legend_handles_unique = (pd.Series(legend_handles, dtype="object").loc[unique_idx]).tolist()

        if len(legend_handles_unique) > 0:
            if float_contrast is True:
                axes_with_legend = contrast_axes
                if show_pairs is True:
                    bta = (1.75, 1.02)
                else:
                    bta = (1.5, 1.02)
            else:
                axes_with_legend = rawdata_axes
                if show_pairs is True:
                    bta = (1.02, 1.)
                else:
                    bta = (1.,1.)
            leg = axes_with_legend.legend(legend_handles_unique,
                                          legend_labels_unique,
                                          bbox_to_anchor=bta,
                                          **legend_kwargs)
            if show_pairs is True:
                for line in leg.get_lines():
                    line.set_linewidth(3.0)

    og_ylim_raw = rawdata_axes.get_ylim()
    og_xlim_raw = rawdata_axes.get_xlim()

    if float_contrast is True:
        # For Gardner-Altman plots only.

        # Normalize ylims and despine the floating contrast axes.
        # Check that the effect size is within the swarm ylims.
        if effect_size_type in ["mean_diff", "cohens_d", "hedges_g","cohens_h"]:
            control_group_summary = plot_data.groupby(xvar)\
                                             .mean(numeric_only=True).loc[current_control, yvar]
            test_group_summary = plot_data.groupby(xvar)\
                                          .mean(numeric_only=True).loc[current_group, yvar]
        elif effect_size_type == "median_diff":
            control_group_summary = plot_data.groupby(xvar)\
                                             .median().loc[current_control, yvar]
            test_group_summary = plot_data.groupby(xvar)\
                                          .median().loc[current_group, yvar]

        if swarm_ylim is None:
            swarm_ylim = rawdata_axes.get_ylim()

        _, contrast_xlim_max = contrast_axes.get_xlim()

        difference = float(results.difference[0])
        
        if effect_size_type in ["mean_diff", "median_diff"]:
            # Align 0 of contrast_axes to reference group mean of rawdata_axes.
            # If the effect size is positive, shift the contrast axis up.
            rawdata_ylims = np.array(rawdata_axes.get_ylim())
            if current_effsize > 0:
                rightmin, rightmax = rawdata_ylims - current_effsize
            # If the effect size is negative, shift the contrast axis down.
            elif current_effsize < 0:
                rightmin, rightmax = rawdata_ylims + current_effsize
            else:
                rightmin, rightmax = rawdata_ylims

            contrast_axes.set_ylim(rightmin, rightmax)

            og_ylim_contrast = rawdata_axes.get_ylim() - np.array(control_group_summary)

            contrast_axes.set_ylim(og_ylim_contrast)
            contrast_axes.set_xlim(contrast_xlim_max-1, contrast_xlim_max)

        elif effect_size_type in ["cohens_d", "hedges_g","cohens_h"]:
            if is_paired:
                which_std = 1
            else:
                which_std = 0
            temp_control = plot_data[plot_data[xvar] == current_control][yvar]
            temp_test    = plot_data[plot_data[xvar] == current_group][yvar]
            
            stds = _compute_standardizers(temp_control, temp_test)
            if is_paired:
                pooled_sd = stds[1]
            else:
                pooled_sd = stds[0]
            
            if effect_size_type == 'hedges_g':
                gby_count   = plot_data.groupby(xvar).count()
                len_control = gby_count.loc[current_control, yvar]
                len_test    = gby_count.loc[current_group, yvar]
                            
                hg_correction_factor = _compute_hedges_correction_factor(len_control, len_test)
                            
                ylim_scale_factor = pooled_sd / hg_correction_factor

            elif effect_size_type == "cohens_h":
                ylim_scale_factor = (np.mean(temp_test)-np.mean(temp_control)) / difference

            else:
                ylim_scale_factor = pooled_sd
                
            scaled_ylim = ((rawdata_axes.get_ylim() - control_group_summary) / ylim_scale_factor).tolist()

            contrast_axes.set_ylim(scaled_ylim)
            og_ylim_contrast = scaled_ylim

            contrast_axes.set_xlim(contrast_xlim_max-1, contrast_xlim_max)

        if one_sankey is None:
            # Draw summary lines for control and test groups..
            for jj, axx in enumerate([rawdata_axes, contrast_axes]):

                # Draw effect size line.
                if jj == 0:
                    ref = control_group_summary
                    diff = test_group_summary
                    effsize_line_start = 1

                elif jj == 1:
                    ref = 0
                    diff = ref + difference
                    effsize_line_start = contrast_xlim_max-1.1

                xlimlow, xlimhigh = axx.get_xlim()

                # Draw reference line.
                axx.hlines(ref,            # y-coordinates
                        0, xlimhigh,  # x-coordinates, start and end.
                        **reflines_kwargs)
                            
                # Draw effect size line.
                axx.hlines(diff,
                        effsize_line_start, xlimhigh,
                        **reflines_kwargs)
        else: 
            ref = 0
            diff = ref + difference
            effsize_line_start = contrast_xlim_max - 0.9
            xlimlow, xlimhigh = contrast_axes.get_xlim()
            # Draw reference line.
            contrast_axes.hlines(ref,            # y-coordinates
                    effsize_line_start, xlimhigh,  # x-coordinates, start and end.
                    **reflines_kwargs)
                        
            # Draw effect size line.
            contrast_axes.hlines(diff,
                    effsize_line_start, xlimhigh,
                    **reflines_kwargs)    
        rawdata_axes.set_xlim(og_xlim_raw) # to align the axis
        # Despine appropriately.
        sns.despine(ax=rawdata_axes,  bottom=True)
        sns.despine(ax=contrast_axes, left=True, right=False)

        # Insert break between the rawdata axes and the contrast axes
        # by re-drawing the x-spine.
        rawdata_axes.hlines(og_ylim_raw[0],                  # yindex
                            rawdata_axes.get_xlim()[0], 1.3, # xmin, xmax
                            **redraw_axes_kwargs)
        rawdata_axes.set_ylim(og_ylim_raw)

        contrast_axes.hlines(contrast_axes.get_ylim()[0],
                             contrast_xlim_max-0.8, contrast_xlim_max,
                             **redraw_axes_kwargs)


    else:
        # For Cumming Plots only.

        # Set custom contrast_ylim, if it was specified.
        if plot_kwargs['contrast_ylim'] is not None or (plot_kwargs['delta2_ylim'] is not None and show_delta2):

            if plot_kwargs['contrast_ylim'] is not None:
                custom_contrast_ylim = plot_kwargs['contrast_ylim']
                if plot_kwargs['delta2_ylim'] is not None and show_delta2:
                    custom_delta2_ylim = plot_kwargs['delta2_ylim']
                    if custom_contrast_ylim!=custom_delta2_ylim:
                        err1 = "Please check if `contrast_ylim` and `delta2_ylim` are assigned"
                        err2 = "with same values."
                        raise ValueError(err1 + err2)
            else:
                custom_delta2_ylim = plot_kwargs['delta2_ylim']
                custom_contrast_ylim = custom_delta2_ylim

            if len(custom_contrast_ylim) != 2:
                err1 = "Please check `contrast_ylim` consists of "
                err2 = "exactly two numbers."
                raise ValueError(err1 + err2)

            if effect_size_type == "cliffs_delta":
                # Ensure the ylims for a cliffs_delta plot never exceed [-1, 1].
                l = plot_kwargs['contrast_ylim'][0]
                h = plot_kwargs['contrast_ylim'][1]
                low = -1 if l < -1 else l
                high = 1 if h > 1 else h
                contrast_axes.set_ylim(low, high)
            else:
                contrast_axes.set_ylim(custom_contrast_ylim)

        # If 0 lies within the ylim of the contrast axes,
        # draw a zero reference line.
        contrast_axes_ylim = contrast_axes.get_ylim()
        if contrast_axes_ylim[0] < contrast_axes_ylim[1]:
            contrast_ylim_low, contrast_ylim_high = contrast_axes_ylim
        else:
            contrast_ylim_high, contrast_ylim_low = contrast_axes_ylim
        if contrast_ylim_low < 0 < contrast_ylim_high:
            contrast_axes.axhline(y=0, **reflines_kwargs)

        if is_paired == "baseline" and show_pairs == True:
            if proportional == True and one_sankey == False:
                rightend_ticks_raw = np.array([len(i)-2 for i in idx]) + np.array(ticks_to_start_sankey)
            else:    
                rightend_ticks_raw = np.array([len(i)-1 for i in temp_idx]) + np.array(ticks_to_skip)
            for ax in [rawdata_axes]:
                sns.despine(ax=ax, bottom=True)
        
                ylim = ax.get_ylim()
                xlim = ax.get_xlim()
                redraw_axes_kwargs['y'] = ylim[0]
        
                if proportional == True and one_sankey == False:
                    for k, start_tick in enumerate(ticks_to_start_sankey):
                        end_tick = rightend_ticks_raw[k]
                        ax.hlines(xmin=start_tick, xmax=end_tick,
                              **redraw_axes_kwargs)
                else:   
                    for k, start_tick in enumerate(ticks_to_skip):
                        end_tick = rightend_ticks_raw[k]
                        ax.hlines(xmin=start_tick, xmax=end_tick,
                              **redraw_axes_kwargs)
                ax.set_ylim(ylim)
                del redraw_axes_kwargs['y']
            
            temp_length = [(len(i)-1)*2-1 for i in idx]
            if proportional == True and one_sankey == False:
                rightend_ticks_contrast = np.array([len(i)-2 for i in idx]) + np.array(ticks_to_start_sankey)
            else:   
                rightend_ticks_contrast = np.array(temp_length) + np.array(ticks_to_skip_contrast)
            for ax in [contrast_axes]:
                sns.despine(ax=ax, bottom=True)
        
                ylim = ax.get_ylim()
                xlim = ax.get_xlim()
                redraw_axes_kwargs['y'] = ylim[0]
        
                if proportional == True and one_sankey == False:
                    for k, start_tick in enumerate(ticks_to_start_sankey):
                        end_tick = rightend_ticks_contrast[k]
                        ax.hlines(xmin=start_tick, xmax=end_tick,
                                **redraw_axes_kwargs)
                else:
                    for k, start_tick in enumerate(ticks_to_skip_contrast):
                        end_tick = rightend_ticks_contrast[k]
                        ax.hlines(xmin=start_tick, xmax=end_tick,
                                **redraw_axes_kwargs)                
        
                ax.set_ylim(ylim)
                del redraw_axes_kwargs['y']
        else:
            # Compute the end of each x-axes line.
            if proportional == True and one_sankey == False:
                rightend_ticks = np.array([len(i)-2 for i in idx]) + np.array(ticks_to_start_sankey)
            else:
                rightend_ticks = np.array([len(i)-1 for i in idx]) + np.array(ticks_to_skip)
        
            for ax in [rawdata_axes, contrast_axes]:
                sns.despine(ax=ax, bottom=True)
            
                ylim = ax.get_ylim()
                xlim = ax.get_xlim()
                redraw_axes_kwargs['y'] = ylim[0]
            
                if proportional == True and one_sankey == False:
                    for k, start_tick in enumerate(ticks_to_start_sankey):
                        end_tick = rightend_ticks[k]
                        ax.hlines(xmin=start_tick, xmax=end_tick,
                                **redraw_axes_kwargs)
                else:
                    for k, start_tick in enumerate(ticks_to_skip):
                        end_tick = rightend_ticks[k]
                        ax.hlines(xmin=start_tick, xmax=end_tick,
                                **redraw_axes_kwargs)
            
                ax.set_ylim(ylim)
                del redraw_axes_kwargs['y']

    if show_delta2 is True or show_mini_meta is True:
        ylim = contrast_axes.get_ylim()
        redraw_axes_kwargs['y'] = ylim[0]
        x_ticks = contrast_axes.get_xticks()
        contrast_axes.hlines(xmin=x_ticks[-2], xmax=x_ticks[-1],
                              **redraw_axes_kwargs)
        del redraw_axes_kwargs['y']

    # Set raw axes y-label.
    swarm_label = plot_kwargs['swarm_label']
    if swarm_label is None and yvar is None:
        swarm_label = "value"
    elif swarm_label is None and yvar is not None:
        swarm_label = yvar

    bar_label = plot_kwargs['bar_label']
    if bar_label is None and effect_size_type != "cohens_h":
        bar_label = "proportion of success"
    elif bar_label is None and effect_size_type == "cohens_h":
        bar_label = "value"

    # Place contrast axes y-label.
    contrast_label_dict = {'mean_diff': "mean difference",
                           'median_diff': "median difference",
                           'cohens_d': "Cohen's d",
                           'hedges_g': "Hedges' g",
                           'cliffs_delta': "Cliff's delta",
                           'cohens_h': "Cohen's h"}

    if proportional == True and effect_size_type != "cohens_h":
        default_contrast_label = "proportion difference"
    else:
        default_contrast_label = contrast_label_dict[EffectSizeDataFrame.effect_size]


    if plot_kwargs['contrast_label'] is None:
        if is_paired:
            contrast_label = "paired\n{}".format(default_contrast_label)
        else:
            contrast_label = default_contrast_label
        contrast_label = contrast_label.capitalize()
    else:
        contrast_label = plot_kwargs['contrast_label']

    contrast_axes.set_ylabel(contrast_label)
    if float_contrast is True:
        contrast_axes.yaxis.set_label_position("right")

    # Set the rawdata axes labels appropriately
    if proportional == False:
        rawdata_axes.set_ylabel(swarm_label)
    else:
        rawdata_axes.set_ylabel(bar_label)
    rawdata_axes.set_xlabel("")

    # Because we turned the axes frame off, we also need to draw back
    # the y-spine for both axes.
    if float_contrast==False:
        rawdata_axes.set_xlim(contrast_axes.get_xlim())
    og_xlim_raw = rawdata_axes.get_xlim()
    rawdata_axes.vlines(og_xlim_raw[0],
                         og_ylim_raw[0], og_ylim_raw[1],
                         **redraw_axes_kwargs)

    og_xlim_contrast = contrast_axes.get_xlim()

    if float_contrast is True:
        xpos = og_xlim_contrast[1]
    else:
        xpos = og_xlim_contrast[0]

    og_ylim_contrast = contrast_axes.get_ylim()
    contrast_axes.vlines(xpos,
                         og_ylim_contrast[0], og_ylim_contrast[1],
                         **redraw_axes_kwargs)


    if show_delta2 is True:
        if plot_kwargs['delta2_label'] is None:
            delta2_label = "delta - delta"
        else: 
            delta2_label = plot_kwargs['delta2_label']
        delta2_axes = contrast_axes.twinx()
        delta2_axes.set_frame_on(False)
        delta2_axes.set_ylabel(delta2_label)
        og_xlim_delta = contrast_axes.get_xlim()
        og_ylim_delta = contrast_axes.get_ylim()
        delta2_axes.set_ylim(og_ylim_delta)
        delta2_axes.vlines(og_xlim_delta[1],
                         og_ylim_delta[0], og_ylim_delta[1],
                         **redraw_axes_kwargs)

    # Make sure no stray ticks appear!
    rawdata_axes.xaxis.set_ticks_position('bottom')
    rawdata_axes.yaxis.set_ticks_position('left')
    contrast_axes.xaxis.set_ticks_position('bottom')
    if float_contrast is False:
        contrast_axes.yaxis.set_ticks_position('left')

    # Reset rcParams.
    for parameter in _changed_rcParams:
        plt.rcParams[parameter] = original_rcParams[parameter]

    # Return the figure.
    return fig