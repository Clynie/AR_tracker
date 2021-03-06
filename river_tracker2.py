'''Link ARs found in different time slices to form tracks


Input data:

1. AR records at individual time steps. This should be the output from
river_tracker1.py in csv format.



Author: guangzhi XU (xugzhi1987@gmail.com; guangzhi.xu@outlook.com)
Update time: 2018-12-05 13:19:09.
'''

from __future__ import print_function

#--------------Globals------------------------------------------
YEAR=2007

SOURCEDIR='/home/guangzhi/datasets/erai/ERAI_AR_THR/2004/'
RECORD_FILE='ar_records_2004-01-01_00-00-00-2004-03-31_18-00-00.csv'
OUTPUTDIR='/home/guangzhi/datasets/erai/ERAI_AR_THR/2004/'

SCHEMATIC=True   # plot schematic or not

LAT1=0; LAT2=90; LON1=80; LON2=440         # domain to plot

TRACK_PARAMS={}
# Int, hours, gap allowed to link 2 records. Should be the time resolution of
# the data.
TRACK_PARAMS['time_gap_allow']=6
# int, number of anchor points along the axis
TRACK_PARAMS['num_anchors']=7
# tracking scheme. 'simple': all tracks are simple paths.
# 'full': use the network scheme, tracks are connected by their joint points.
TRACK_PARAMS['track_scheme']='simple'  # 'simple' | 'full'
# int, max Hausdorff distance in km to define a neighborhood relationship
TRACK_PARAMS['max_dist_allow']=1200  # km
# int, min duration in hrs to keep a track.
TRACK_PARAMS['min_duration']=24
# int, min number of non-relaxed records in a track to keep a track.
TRACK_PARAMS['min_nonrelax']=1







#--------Import modules-------------------------
import os
import numpy as np
import pandas as pd
from utils import funcs,plot
import copy
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap
import matplotlib.patches as patches






#######################################################################
#                           Util functions                            #
#######################################################################

class AR(object):
    '''Ojbect representing an AR'''
    total_count=0

    def __init__(self,id,data):
        self.id=id
        self.data=data
        self.finish=False
        AR.total_count+=1
        self.linked=[]

    @property
    def coor(self):
        ts=self.data['time']
        ys=self.data['centroid_y']
        xs=self.data['centroid_x']
        return np.array([ts,ys,xs]).T

    @property
    def lats(self):
        return self.data['axis_y'].iloc[-1]

    @property
    def lons(self):
        return self.data['axis_x'].iloc[-1]

    @property
    def rdp_lats(self):
        return self.data['axis_rdp_y'].iloc[-1]

    @property
    def rdp_lons(self):
        return self.data['axis_rdp_x'].iloc[-1]

    @property
    def anchor_lats(self):
        return getAnchors(self.lats)

    @property
    def anchor_lons(self):
        return getAnchors(self.lons)

    @property
    def times(self):
        self.data=self.data.sort_values(by='time')
        return self.data.time

    @property
    def latest(self):
        self.data=self.data.sort_values(by='time')
        return self.data.iloc[-1]

    @property
    def duration(self):
        return self.latest.time-self.data.time.iloc[0]

    def forwardHausdorff(self,lats,lons):

        return forwardHausdorff(self.anchor_lats,self.anchor_lons,lats,lons)

    def backwardHausdorff(self,lats,lons):

        return forwardHausdorff(lats,lons,self.anchor_lats,self.anchor_lons)

    def Hausdorff(self,lats,lons):

        fh=self.forwardHausdorff(lats,lons)
        bh=self.backwardHausdorff(lats,lons)
        return max(fh,bh)

    def append(self,ar):
        if not self.finish:
            if type(ar) is AR:
                ar=ar.data
            self.data=pd.concat([self.data,ar],ignore_index=True)
            self.data=self.data.sort_values(by='time')


def forwardHausdorff(lats1,lons1,lats2,lons2):
    '''Compute forward Hausdorff distance betweem 2 tracks

    Args:
        lats1 (list or 1D array): latitudes of track1.
        lons1 (list or 1D array): longitudes of track1.
        lats2 (list or 1D array): latitudes of track2.
        lons2 (list or 1D array): longitudes of track2.
    Returns:
        forward Hausdorff distance in km.
    '''

    dists=[]
    for ii in range(len(lats1)):
        latii=lats1[ii]
        lonii=lons1[ii]
        distsii=funcs.greatCircle(latii,lonii,lats2,lons2)/1e3 #km
        dists.append(np.min(distsii))

    return np.max(dists)


def getAnchors(arr):
    '''Get anchor points along from an axis.

    Args:
        arr (ndarray): 1D array from which to sample the anchor points.
    Returns:
        (ndarray): 1D array of the sampled anchor points from <arr>.
    '''

    nn=min(len(arr), TRACK_PARAMS['num_anchors'])
    idx=np.around(np.linspace(0,len(arr)-1,nn),0).astype('int')

    return np.take(arr,idx)


def plotHD(y1,x1,y2,x2,timelabel=None,linkflag='',ax=None,show=True):
    '''Plot Hausdorff links'''

    if ax is None:
        figure=plt.figure(figsize=(12,6),dpi=100)
        ax=figure.add_subplot(111)

    # plot respective axes
    n1=len(y1)
    n2=len(y2)
    ax.plot(x1,y1,'b:o',markersize=4)
    ax.plot(x2,y2,'c:o',markersize=4)

    # forward Hausdorff
    fh_mins={}
    for ii in range(n1):
        yii=y1[ii]
        xii=x1[ii]
        distsii=funcs.greatCircle(yii,xii,y2,x2)/1e3 #km
        idx=np.argmin(distsii)
        minii=np.min(distsii)
        fh_mins[((xii,x2[idx]),(yii,y2[idx]))]=minii

    # backward Hausdorff
    bh_mins={}
    for ii in range(n2):
        yii=y2[ii]
        xii=x2[ii]
        distsii=funcs.greatCircle(yii,xii,y1,x1)/1e3 #km
        idx=np.argmin(distsii)
        minii=np.min(distsii)
        bh_mins[((xii,x1[idx]),(yii,y1[idx]))]=minii

    # highlight max
    fhmax_idx=sorted(fh_mins,key=fh_mins.get)[-1]
    bhmax_idx=sorted(bh_mins,key=bh_mins.get)[-1]

    # make an arrow showing max dist in forward and backward.
    # NOTE there is a bug in matplotlib 2.0.0 that messed up the arrow() plot,
    # thus this FancyArrowPatch wordaround

    fhmax_x1, fhmax_x2=fhmax_idx[0]
    fhmax_y1, fhmax_y2=fhmax_idx[1]

    style='Simple,head_length=10,head_width=6,tail_width=2'
    arrow=patches.FancyArrowPatch((fhmax_x1, fhmax_y1), (fhmax_x2, fhmax_y2),
            arrowstyle=style,
            fc='b', ec='b')
    ax.add_patch(arrow)

    # plot max dist texts
    ax.text(fhmax_x2, fhmax_y2, '%.1f %s' %(np.max(fh_mins.values()), linkflag),
            fontsize=12, color='b')

    # backward arrows
    bhmax_x1, bhmax_x2=bhmax_idx[0]
    bhmax_y1, bhmax_y2=bhmax_idx[1]

    arrow=patches.FancyArrowPatch((bhmax_x1, bhmax_y1), (bhmax_x2, bhmax_y2),
            arrowstyle=style,
            fc='c', ec='c')
    ax.add_patch(arrow)

    ax.text(bhmax_x2, bhmax_y2, '%.1f %s' %(np.max(bh_mins.values()), linkflag),
            fontsize=12, color='c')

    ax.set_xlabel('Longitude (degree)')
    ax.set_ylabel('Latitude (degree)')
    ax.grid(True,axis='both')

    if timelabel is not None:
        ax.set_title('(a) %s' %timelabel,loc='left')

    if show:
        plt.show(block=False)

    return


def plotAR(arlist,latax,lonax,full=False,ax=None,label=None,linestyle='solid',marker=None):
    '''Plot AR tracks

    Args:
        arlist (list): list of AR objects to plot.

    Kwargs:
        full (bool): if True, plot tracks of an AR from its entire lifecycle.
                     if False, plot only the track of the last time step.
        ax (matplotlib.axis): axis to plot onto.
        label (str or None): type of label to label tracks.
                             'id': label with AR id.
                             'time': label with time stamp.
                             None: don't put label.
        linestyle (str): line style to plot the tracks.
        marker (str): marker to plot track axes.
    '''

    isshow=False

    if ax is None:
        figure=plt.figure(figsize=(12,6),dpi=100)
        ax=figure.add_subplot(111)
        isshow=True

    ax.patch.set_color('0.7')

    if not isinstance(arlist,(tuple,list)):
        arlist=[arlist,]

    bmap=Basemap(projection='cyl',
            llcrnrlat=10,llcrnrlon=90,
            urcrnrlat=latax[-1],urcrnrlon=lonax[-1],
            ax=ax,fix_aspect=False)

    bmap.drawcoastlines(linewidth=0.5,linestyle='solid',color='k',\
        antialiased=True)

    lon_labels=np.array(plot.mkscale(lonax[0],lonax[-1],15,1))
    idx=np.where((lon_labels>=lonax[0]) & (lon_labels<=lonax[-1]))
    lon_labels=np.array(lon_labels)[idx]

    lat_labels=np.array(plot.mkscale(latax[0],latax[-1],15,1))
    idx=np.where((lat_labels>=latax[0]) & (lat_labels<=latax[-1]))
    lat_labels=np.array(lat_labels)[idx]

    parallels=[1,1,0,0]
    meridians=[0,0,0,1]

    bmap.drawparallels(lat_labels,labels=parallels,linewidth=0,\
            labelstyle='+/-',fontsize=14)
    bmap.drawmeridians(lon_labels,labels=meridians,linewidth=0,\
            labelstyle='+/-',fontsize=14)

    #bmap=pobj.bmap

    for ii,arii in enumerate(arlist):
        if not full:
            axis_y=arii.anchor_lats
            axis_x=arii.anchor_lons

            xx,yy=bmap(axis_x,axis_y)
            ax.plot(xx,yy,'bo-')
            x0=xx[0]
            y0=yy[0]
        else:
            #cmap=plt.cm.RdBu_r
            cmap=plt.cm.gnuplot
            for jj in range(len(arii.data)):
                axis_yjj=getAnchors(arii.data['axis_y'].iloc[jj])
                axis_xjj=getAnchors(arii.data['axis_x'].iloc[jj])
                xx,yy=bmap(axis_xjj,axis_yjj)
                if jj!=len(arii.data)-1:
                    alpha=0.7
                else:
                    alpha=1
                    x0=xx[0]
                    y0=yy[0]
                frac=float(jj)/max(1,(len(arii.data)-1))
                ax.plot(xx,yy,alpha=alpha,color=cmap(frac),linestyle=linestyle,
                        marker=marker,markersize=2)


        if label is not None:
            if label=='id':
                if hasattr(arii,'trackid'):
                    labii=arii.trackid
                else:
                    labii=str(arii.id)
            elif label=='time':
                labii=str(arii.latest.time)

            elif isinstance(label,(list,tuple)):
                labii=label[ii]

            ax.text(x0,y0,'%s' %labii, fontsize=10)

    if isshow:
        ax.get_figure().show()

    return


def getDistMatrix(tr_list,newlats,newlons):
    '''Compute distance matrix among track axis anchors

    Args:
        tr_list (list): list of AR objs, existing systems at time t=t.
        newlats (list or 1D array): latitudes at t=t+1.
        newlons (list or 1D array): longitudes at t=t+1.

    Returns:
        dists (ndarray): n*m matrix consisting distances between existing
                         and new tracks. Rows as new records at tnow,
                         columns as existing tracks.
    '''

    dists=np.zeros([len(newlats),len(tr_list)])

    for kk in range(len(newlats)):
        for jj,trjj in enumerate(tr_list):
            if trjj.finish:
                dists[kk,jj]=np.inf
            else:
                fh=trjj.forwardHausdorff(newlats[kk],newlons[kk])
                bh=trjj.backwardHausdorff(newlats[kk],newlons[kk])
                dists[kk,jj]=min(fh,bh)

    return dists


def convarray(text):
    text=text.replace('[','').replace(']','')
    array=np.array(text.split()).astype('float')

    return array



#######################################################################
#                         Tracking functions                          #
#######################################################################

def matchCenters2(tr_list, newrec, params, isplot=False, plot_dir=None,
        verbose=True):
    '''Match and link nearby centers at 2 consecutive time steps

    Args:
        tr_list (list): list of AR objs, existing systems at time t=t.
        newrec (DataFrame): new center data at time t=t+1.
        params (dict): tracking parameters.

    Kwargs:
        isplot (bool): create schematic plot or not.
        plot_dir (str): folder to save schematic plot. Only used if isplot=True.

    Returns:
        tr_list (list): list of AR objs, ARs with new matching records
                        appended at the end.
        allocated_recs (list): list of ints, ids of new records that are
                               attributed to existing systems during the
                               process.

    Matching is based on geo-distances and uses nearest neighbour strategy.
    '''

    time_gap_allow=params['time_gap_allow']
    max_dist_allow=params['max_dist_allow']
    track_scheme=params['track_scheme']
    time_gap_allow=pd.Timedelta(hours=time_gap_allow)

    # coordinates at t+1
    newlats=[getAnchors(newrec.iloc[ii].axis_y) for ii in range(newrec.shape[0])]
    newlons=[getAnchors(newrec.iloc[ii].axis_x) for ii in range(newrec.shape[0])]

    # distance matrix
    dists=getDistMatrix(tr_list,newlats,newlons)

    # get max allowed movements
    max_dists=np.ones(dists.shape)*max_dist_allow

    if isplot:
        figure=plt.figure(figsize=(12,6),dpi=100)
        ax=figure.add_subplot(111)


    def one2One(dists,mask_rows,mask_cols,linkflag):
        '''One to one matching

        Args:
            dists (ndarray): n*m distance matrix, with rows corresponding to
                             new records at t=t+1, columns to existing tracks
                             at t=t.
            mask_rows (list): row ids to block linking.
            mask_cols (list): col ids to block linking.
            linkflag (str): a single char to denote the type of linking,
                            used in generated plot. '' for initial linking,
                            'M' for a merging, 'S' for a splitting.
        Returns:
            got_rows (list): row ids linked during the process.
            got_cols (list): col ids linked during the process.
        '''

        got_rows=[]
        got_cols=[]

        #--------Choose from the smallest distances--------
        while np.min(dists)<=np.max(max_dists):

            distjj=np.min(dists)
            minidx=zip(*np.where(dists==distjj))

            for idy,idx in minidx:
                # need this when max_dists is not uniform
                if distjj>max_dists[idy,idx]:
                    dists[idy,idx]=np.inf
                    continue

                if idx in mask_cols or idy in mask_rows:
                    dists[idy,idx]=np.inf
                    continue

                tr_old=tr_list[idx]
                tr_new=newrec.iloc[[idy]]

                # track has got point, a split happening
                if tr_new.time.iloc[0]==tr_old.latest.time:
                    # retrieve the original track
                    trori=[trjj for trjj in tr_list_ori if trjj.id==tr_old.id][0]

                    #------Make a new copy of the spliting track------
                    tr_old=AR(AR.total_count,trori.data)
                    tr_list.append(tr_old)

                if tr_new.time.iloc[0]-tr_old.latest.time<=time_gap_allow:
                    # make plot before appending
                    if isplot:
                        timestr='%s - %s' %(tr_old.latest.time,
                                tr_new.time.iloc[0])
                        plotHD(tr_old.anchor_lats, tr_old.anchor_lons,
                                newlats[idy], newlons[idy],timelabel=timestr,
                                linkflag=linkflag,
                                ax=ax,show=False)

                    tr_old.append(tr_new)
                    got_rows.append(idy)
                    got_cols.append(idx)
                    dists[idy,idx]=np.inf

                    mask_rows.append(idy)
                    mask_cols.append(idx)

                    if verbose:
                        print('# <matchCenters>: dist: %.2f < (%.2f). Join record to track %d.'\
                            %(distjj,max_dists[idy,idx],tr_old.id))
                else:
                    dists[idy,idx]=np.inf

            # NOTE: need to add to mask_rows mask_cols for each link.
            # as in some really rare cases there could be more than 1 pair
            # sharing the same minimum distance. In such cases, tr_new.time.iloc[0]==tr_old.latest.time,
            # even if the tracking scheme is "simple"
            #mask_rows.extend(got_rows)
            #mask_cols.extend(got_cols)

        return got_rows,got_cols


    # keep a copy of the original tracks for splitting
    if track_scheme=='full':
        tr_list_ori=copy.deepcopy(tr_list)

    #-------------------Stage 1 init link-------------------
    mask_row1, mask_col1=one2One(dists.copy(),[],[],'')

    if track_scheme=='full':
        #-------------------Stage 2 merge link-------------------
        mask_row2, mask_col2=one2One(dists.copy(),[],mask_col1,'M')

        #-------------------Stage 3 split link-------------------
        mask_row3, mask_col3=one2One(dists,mask_row1+mask_row2,[],'S')
    else:
        mask_row2=[]
        mask_row3=[]


    if isplot:
        # plot legend
        ax.plot([],[],'b:o',label='t=t')
        ax.plot([],[],'c:o',label='t=t+1')
        ax.legend(loc=0)
        #----------------- Save plot------------
        if len(mask_row1)>0:
            timestr='%s' %(newrec.time.iloc[0])
            suffix=timestr.replace(':','-').replace(' ','_')
            plot_save_name='linkages_scheme_%s_%s' %(track_scheme,suffix)
            plot_save_name=os.path.join(plot_dir,plot_save_name)
            print('\n# <river_tracker2>: Save figure to', plot_save_name)
            figure.savefig(plot_save_name+'.png',dpi=100,bbox_inches='tight')
            figure.savefig(plot_save_name+'.pdf',dpi=100,bbox_inches='tight')

        plt.close(figure)

    allocated_recs=[newrec.iloc[ii].id for ii in mask_row1+mask_row2+mask_row3]
    #allocated_tracks=[tr_list[ii].id for ii in mask_col1+mask_col2+mask_col3]

    return tr_list, allocated_recs


def trackARs2(record, parameter, plot_dir, verbose=True):
    '''Group records to form tracks

    Args:
        record (DataFrame): AR records at different time slices.
        parameter (dict): tracking parameteres defined in the global preamble.
        plot_dir (str): folder to save schematic plot.

    Returns:
        finished_list (list): list of AR objs. Found tracks.
    '''

    time_gap_allow=parameter['time_gap_allow']
    time_gap_allow=pd.Timedelta(hours=time_gap_allow)

    record.loc[:,'time']=pd.to_datetime(record.time)
    timelist=record.time.dropna(how='any').unique()
    timelist=pd.to_datetime(timelist).sort_values()

    #----------------Loop through time----------------
    track_list=[]
    finished_list=[]

    for ii,tnow in enumerate(timelist):

        if verbose:
            print('\n# <trackARs>: Allocating record at time:', tnow)

        recii=record[record.time==tnow]

        #--------Create new ars when 1st record is read--------
        if len(track_list)==0:
            for jj in range(recii.shape[0]):
                recjj=recii.iloc[[jj]]
                trjj=AR(AR.total_count,recjj)
                track_list.append(trjj)
            continue

        #------------End existing ars if gap too long---------------
        if len(track_list)>0:
            for trjj in track_list:
                if tnow-trjj.latest.time>time_gap_allow:
                    trjj.finish=True
                    finished_list.append(trjj)
                    track_list.remove(trjj)

        if len(track_list)==0:
            continue

        #-------------------Link tracks-------------------
        all_rec_id=recii.id.tolist()
        track_list,allocated_recs=matchCenters2(track_list, recii, parameter,
                isplot=SCHEMATIC, plot_dir=plot_dir)

        #-----------------Create a new ar for left-overs-----------------
        left_rec_id=set(all_rec_id).difference(allocated_recs)
        if len(left_rec_id)>0:
            for jj in left_rec_id:
                trjj=AR(AR.total_count,recii[recii.id==jj])
                track_list.append(trjj)

        #----Put all to finished list at last time step----
        if ii==len(timelist)-1:
            finished_list.extend(track_list)


    return finished_list


def filterTracks(tr_list,parameter,verbose=True):
    '''Filter tracks

    Args:
        tr_list (list): list of AR objects, found tracks.
        parameter (dict): tracking parameteres defined in the global preamble.

    Returns:
        tr_list (list): list of AR objects, filtered tracks.

    Tracks that are filtered:
        * tracks that are too short, controlled by 'min_duration'
        * tracks that start over land (all rdp axis points are over land at
          t=0).
        * tracks that consist of solely relaxed records.
        * tracks outside of latitude region, not in use.
    '''

    min_duration=parameter['min_duration']
    min_nonrelax=parameter['min_nonrelax']

    #---------------Remove short tracks---------------
    new_list=[ii for ii in tr_list if ii.duration>=\
            pd.Timedelta(hours=min_duration)]
    tr_list=new_list

    #-----Remove tracks consisting too many relaxed segs-----
    new_list=[]
    for tt in tr_list:
        relaxed=tt.data.is_relaxed.tolist()
        if relaxed.count(True)>=min_nonrelax:
            new_list.append(tt)
    tr_list=new_list


    return tr_list







#-------------Main---------------------------------
if __name__=='__main__':

    #-----------Read in records---------------------
    abpath_in=os.path.join(SOURCEDIR,RECORD_FILE)
    print('\n### <river_tracker2>: Read in file:\n',abpath_in)

    keys=['id', 'time', 'contour_y', 'contour_x', 'centroid_y', 'centroid_x',
            'axis_y', 'axis_x', 'axis_rdp_y', 'axis_rdp_x',
            'area', 'length', 'width', 'iso_quotient', 'LW_ratio',
            'strength', 'strength_ano', 'strength_std',
            'mean_angle', 'is_relaxed']

    convkeys=['contour_y', 'contour_x',
            'axis_y', 'axis_x', 'axis_rdp_y', 'axis_rdp_x']

    converters=dict([(keyii, convarray) for keyii in convkeys])

    dtypes={'id': 'int', 'time': 'str',
            'area': np.float64, 'length': np.float64, 'width': np.float64,
            'iso_quotient': np.float64, 'LW_ratio': np.float64,
            'strength': np.float64, 'strength_ano': np.float64,
            'strength_std': np.float64,
            'mean_angle': np.float64, 'is_relaxed': 'bool'}

    ardf=pd.read_csv(abpath_in,dtype=dtypes,converters=converters)

    if not os.path.exists(OUTPUTDIR):
        os.makedirs(OUTPUTDIR)

    if SCHEMATIC:
        plot_dir=os.path.join(OUTPUTDIR, 'plots')
        if not os.path.exists(plot_dir):
            os.makedirs(plot_dir)

    #-------------------Track ars-------------------
    track_list=trackARs2(ardf,TRACK_PARAMS,plot_dir)

    #------------------Filter tracks------------------
    track_list=filterTracks(track_list,TRACK_PARAMS)

    #-------------------Save output-------------------
    latax=np.arange(LAT1, LAT2)
    lonax=np.arange(LON1, LON2)

    for ii in range(len(track_list)):
        tii=track_list[ii]
        trackidii='%d%d' %(tii.data.loc[0,'time'].year, ii+1)
        tii.data.loc[:,'trackid']=trackidii
        tii.trackid=trackidii

        if ii==0:
            trackdf=tii.data
        else:
            trackdf=pd.concat([trackdf,tii.data],ignore_index=True)

        figure=plt.figure(figsize=(12,6),dpi=100)
        ax=figure.add_subplot(111)
        plotAR(tii,latax,lonax,True,ax=ax)

        #----------------- Save plot------------
        plot_save_name='ar_track_%s' %trackidii
        plot_save_name=os.path.join(plot_dir,plot_save_name)
        print('\n# <river_tracker2>: Save figure to', plot_save_name)
        figure.savefig(plot_save_name+'.png',dpi=100,bbox_inches='tight')

        plt.close(figure)


    #--------Save------------------------------------
    abpath_out=os.path.join(OUTPUTDIR,'ar_tracks_%d.csv' %YEAR)
    print('\n### <river_tracker2>: Saving output to:\n',abpath_out)
    trackdf.to_csv(abpath_out,index=False)
