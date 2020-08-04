#
#####################################################################
# Shaders

easeCode = \
    """
    #define M_PI 3.1415926535897932384626433832795

    float easeInOutSine(float pos) {
    #ifdef FLOW
        return pos;
    #else
        return 0.5 * (1.0 - cos(M_PI * pos));
    #endif
    }
    """

rotateShader = easeCode + \
    """
    uniform float deltaAngle;
    uniform float scale;
    uniform float time;
    uniform float duration;
    uniform float scaleZ;

    vec4 getPointSample(vec4 xyzw);

    vec4 rotate(vec4 xyzw) {
        vec4 point = getPointSample(xyzw);

        float start = point.w;
        float pos = (time - start) / abs(duration);
        if(duration < 0.0) pos = 1.0 - pos;
        if(pos < 0.0) return vec4(point.xyz, 0.0);
        if(pos > 1.0) pos = 1.0;
        pos = easeInOutSine(pos);
        float c = cos(deltaAngle * pos);
        float s = sin(deltaAngle * pos);
        point.xy = vec2(point.x * c - point.y * s, point.x * s + point.y * c)
            * pow(scale, pos);
        if(scaleZ != 0.0) point.z *= pow(scaleZ, pos);
        return vec4(point.xyz, 0.0);
    }
    """

diagShader = easeCode + \
    """
    uniform float scaleX;
    uniform float scaleY;
    uniform float scaleZ;
    uniform float time;
    uniform float duration;

    vec4 getPointSample(vec4 xyzw);

    vec4 rotate(vec4 xyzw) {
        vec4 point = getPointSample(xyzw);

        float start = point.w;
        float pos = (time - start) / abs(duration);
        if(duration < 0.0) pos = 1.0 - pos;
        if(pos < 0.0) return vec4(point.xyz, 0.0);
        if(pos > 1.0) pos = 1.0;

        pos = easeInOutSine(pos);
        point.x *= pow(scaleX, pos);
        point.y *= pow(scaleY, pos);
        if(scaleZ != 0.0) point.z *= pow(scaleZ, pos);
        return vec4(point.xyz, 0.0);
    }
    """

shearShader = easeCode + \
    """
    uniform float scale;
    uniform float translate;
    uniform float time;
    uniform float duration;
    uniform float scaleZ;

    vec4 getPointSample(vec4 xyzw);

    vec4 shear(vec4 xyzw) {
        vec4 point = getPointSample(xyzw);

        float start = point.w;
        float pos = (time - start) / abs(duration);
        if(duration < 0.0) pos = 1.0 - pos;
        if(pos < 0.0) return vec4(point.xyz, 0.0);
        if(pos > 1.0) pos = 1.0;

        pos = easeInOutSine(pos);
        float s = pow(scale, pos);
        point.x  = s * (point.x + translate * pos * point.y);
        point.y *= s;
        if(scaleZ != 0.0) point.z *= pow(scaleZ, pos);
        return vec4(point.xyz, 0.0);
    }
    """

colorShader = easeCode + \
    """
    uniform float time;
    uniform float duration;

    vec4 getPointSample(vec4 xyzw);
    vec4 getColorSample(vec4 xyzw);

    vec3 hsv2rgb(vec3 c) {
      vec4 K = vec4(1.0, 2.0 / 3.0, 1.0 / 3.0, 3.0);
      vec3 p = abs(fract(c.xxx + K.xyz) * 6.0 - K.www);
      return c.z * mix(K.xxx, clamp(p - K.xxx, 0.0, 1.0), c.y);
    }

    #ifdef FLOW
    #define TRANSITION 0.0
    #else
    #define TRANSITION 0.2
    #endif

    vec4 getColor(vec4 xyzw) {
        vec4 color = getColorSample(xyzw);
        vec4 point = getPointSample(xyzw);

        float start = point.w;
        float pos, ease;
        pos = (time - start) / abs(duration);
        if(duration < 0.0) pos = 1.0 - pos;
        if(pos < 0.0) pos = 0.0;
        else if(pos > 1.0) pos = 1.0;

        if(pos < TRANSITION) {
            ease = easeInOutSine(pos / TRANSITION);
            color.w *= ease * 0.6 + 0.4;
            color.y *= ease * 0.6 + 0.4;
        }
        else if(pos > 1.0 - TRANSITION) {
            ease = easeInOutSine((1.0 - pos) / TRANSITION);
            color.w *= ease * 0.6 + 0.4;
            color.y *= ease * 0.6 + 0.4;
        }
        return vec4(hsv2rgb(color.xyz), color.w);
    }
    """

sizeShader = easeCode + \
    """
    uniform float time;
    uniform float small;
    uniform float duration;

    vec4 getPointSample(vec4 xyzw);

    #ifdef FLOW
    #define TRANSITION 0.0
    #else
    #define TRANSITION 0.2
    #endif
    #define BIG (small * 7.0 / 5.0)

    vec4 getSize(vec4 xyzw) {
        vec4 point = getPointSample(xyzw);

        float start = point.w;
        float pos, ease, size = BIG;
        pos = (time - start) / abs(duration);
        if(duration < 0.0) pos = 1.0 - pos;
        if(pos < 0.0) pos = 0.0;
        else if(pos > 1.0) pos = 1.0;

        if(pos < TRANSITION) {
            ease = easeInOutSine(pos / TRANSITION);
            size = small * (1.0-ease) + BIG * ease;
        }
        else if(pos > 1.0 - TRANSITION) {
            ease = easeInOutSine((1.0 - pos) / TRANSITION);
            size = small * (1.0-ease) + BIG * ease;
        }
        return vec4(size, 0.0, 0.0, 0.0);
    }
    """


######################################################################
# Utility functions

HSVtoRGB = (h, s, v) ->
    i = Math.floor(h * 6);
    f = h * 6 - i;
    p = v * (1 - s);
    q = v * (1 - f * s);
    t = v * (1 - (1 - f) * s);
    switch i % 6
        when 0 then [v, t, p]
        when 1 then [q, v, p]
        when 2 then [p, v, t]
        when 3 then [p, q, v]
        when 4 then [t, p, v]
        when 5 then [v, p, q]

expLerp = (a, b) -> (t) -> Math.pow(b, t) * Math.pow(a, 1-t)
linLerp = (a, b) -> (t) -> b*t + a*(1-t)
polyLerp = (a, b, n) -> (t) -> Math.pow(t, n) * (b-a) + a
discLerp = (a, b, n) -> (t) -> Math.floor(Math.random() * (n+1)) * (b-a)/n + a
randElt = (l) -> l[Math.floor(Math.random() * l.length)]
randSign = () -> randElt [-1, 1]

extend = (obj, src) ->
    for key, val of src
        obj[key] = val if src.hasOwnProperty key


######################################################################
# View class

# This displays the points from a Controller class into a view

class DynamicsView
    constructor: (opts) ->
        opts ?= {}
        @is3D       = opts.is3D ? false
        @axisColors = opts.axisColors?.slice() ? []
        @refColor   = opts.refColor ? "rgb(80, 120, 255)"
        @timer      = opts.timer ? true
        @axisOpts   =
            end:     false
            width:   3
            zBias:   -1
            depth:   1
            color:   "black"
            range:   [-10,10]
        extend @axisOpts, (opts.axisOpts ? {})

        @axisColors[0] ?= [0, 0, 0, 0.3]
        @axisColors[1] ?= [0, 0, 0, 0.3]
        @axisColors[2] ?= [0, 0, 0, 0.3]

        @mathbox = null
        # Un-transformed view
        @view0 = null
        # Transformed view
        @view = null
        @initialized = false

        @shaderElt    = null
        @linesElt     = null
        @linesDataElt = null

    setCoords: (v1, v2, v3) =>
        v1[2] ?= 0
        v2[2] ?= 0
        v3 ?= [0,0,1]
        @v1 = v1
        @v2 = v2
        @v3 = v3
        # Compute extents
        @coordMat = new THREE.Matrix4().set \
            v1[0], v2[0], v3[0], 0,
            v1[1], v2[1], v3[1], 0,
            v1[2], v2[2], v3[2], 0,
                0,     0,     0, 1
        cmi = @coordMatInv = new THREE.Matrix4().getInverse @coordMat
        corners = [
            new THREE.Vector3( 1, 1, 1),
            new THREE.Vector3(-1, 1, 1),
            new THREE.Vector3( 1,-1, 1),
            new THREE.Vector3( 1, 1,-1)
        ].map (c) -> c.applyMatrix4 cmi
        rad = Math.max.apply null, corners.map (c) -> c.length()
        @extents =
            rad:  rad
            x:    Math.max.apply null, corners.map (c) -> Math.abs c.x
            y:    Math.max.apply null, corners.map (c) -> Math.abs c.y
            z:    Math.max.apply null, corners.map (c) -> Math.abs c.z
        @controller?.recomputeExtents()

    # Must be called after @setcoords() and @loadDynamics()
    updateView: (mathbox, view) =>
        @mathbox ?= mathbox
        @view0 ?= view

        if @view
            @view.set 'matrix', @coordMat
        else
            @view = @view0.transform matrix: @coordMat
            for i in (if @is3D then [1,2,3] else [1,2])
                @axisOpts.axis    = i
                @axisOpts.color   = @axisColors[i-1]
                @axisOpts.opacity = @axisColors[i-1][3]
                @view.axis @axisOpts
        canvas = @mathbox._context.canvas

        flow = @controller.flow
        numPointsRow = @controller.numPointsRow
        numPointsCol = @controller.numPointsCol
        numPointsDep = @controller.numPointsDep

        if @initialized
            params = @current.shaderParams()
            if flow
                params.code = "#define FLOW\n" + params.code
            @shaderElt.set params
            @linesDataElt.set @current.linesParams()

        else
            pointsOpts =
                id:       "points-orig"
                channels: 4
                width:    numPointsRow
                height:   numPointsCol
                data:     @controller.points
                live:     false
            if @is3D
                pointsOpts.depth = numPointsDep
                pointsType = @view.voxel
            else
                pointsType = @view.matrix
            @pointsElt = pointsType pointsOpts
            params = @current.shaderParams()
            if flow
                params.code = "#define FLOW\n" + params.code
            controller = @controller
            if @timer
                timer = (t) -> controller.curTime = t
            else
                timer = (t) -> controller.curTime
            @shaderElt = @pointsElt.shader params,
                time: timer
                duration: () => @controller.duration * @controller.direction
            @shaderElt.resample id: "points"

            # Coloring pipeline
            pointsOpts =
                channels: 4
                width:    numPointsRow
                height:   numPointsCol
                data:     @controller.colors
                live:     false
            if @is3D
                pointsOpts.depth = numPointsDep
                pointsType = @view.voxel
            else
                pointsType = @view.matrix
            pointsType pointsOpts
            .shader
                code:    (if flow then "#define FLOW\n" else "") + colorShader
                sources: [@pointsElt]
            ,
                time: () -> controller.curTime
                duration: () => @controller.duration * @controller.direction
            .resample id: "colors"

            # Size pipeline
            @view0
                .shader
                    code:  (if flow then "#define FLOW\n" else "") + sizeShader
                ,
                    time:  () -> controller.curTime
                    small: () -> 5 / 739 * canvas.clientWidth
                    duration: () => @controller.duration * @controller.direction
                .resample
                    source: @pointsElt
                    id:     "sizes"

            # @view
            #     .point
            #         points: "#points"
            #         color:  "white"
            #         colors: "#colors"
            #         size:   1
            #         sizes:  "#sizes"
            #         zBias:  1
            #         zIndex: 2

            # Reference lines
            @linesDataElt = @view.matrix @current.linesParams()
            @linesElt = @view.line
                color:    @refColor
                width:    if @is3D then 5 else 2
                opacity:  if @is3D then 0.8 else 0.4
                zBias:    0
                zIndex:   1

            @initialized = true

    # Must be called after @setcoords()
    loadDynamics: (dynamics) =>
        @current = dynamics

        @matrixOrigCoords = new THREE.Matrix4()
            .multiply(@coordMat)
            .multiply(@current.stepMat)
            .multiply(@coordMatInv)

    # Choose random (but not too wonky) coordinate system
    randomizeCoords: () =>
        v1 = [0, 0]
        v2 = [0, 0]
        # Vector length between 1/2 and 2
        distribution = linLerp 0.5, 2
        len = distribution Math.random()
        θ = Math.random() * 2 * π
        v1[0] = Math.cos(θ) * len
        v1[1] = Math.sin(θ) * len
                # Angle between vectors between 45 and 135 degrees
        θoff = randSign() * linLerp(π/4, 3*π/4)(Math.random())
        len = distribution Math.random()
        v2[0] = Math.cos(θ + θoff) * len
        v2[1] = Math.sin(θ + θoff) * len
        @setCoords v1, v2


######################################################################
# Controller class

# This one just moves points around in a standard coordinate system

class Controller
    constructor: (opts) ->
        opts ?= {}
        @numPointsRow = opts.numPointsRow ? 0
        @numPointsCol = opts.numPointsCol ? 0
        @numPointsDep = opts.numPointsDep ? 0
        @duration     = opts.duration     ? 3.0
        @continuous   = opts.continuous   ? false
        @is3D         = opts.is3D         ? false
        @flow         = opts.flow         ? false  # For testing distributions

        # Active views: set these before loading a demo
        @views = []
        @extents =
            rad: 0
            x:   0
            y:   0
            z:   0

        # Current demo
        @current = null
        # Playing forward or backward
        @direction = 1

        @numPointsDep = 1 unless @is3D
        @numPoints = @numPointsRow * @numPointsCol * @numPointsDep - 1

        @curTime = 0
        @startTime = -@duration  # when continuous is off
        @points = [[0, 0, 0, 1e15]]

        # Colors
        @colors = [[0, 0, 0, 1]].concat([Math.random(), 1, 0.7, 1] for [0...@numPoints])

    addView: (view) =>
        view.controller = @
        @views.push view
        @recomputeExtents()

    recomputeExtents: () =>
        @extents =
            rad: 0
            x:   0
            y:   0
            z:   0
        for view in @views
            for prop in ["rad", "x", "y", "z"]
                @extents[prop] = Math.max @extents[prop], view.extents[prop]

    loadDynamics: (type, opts) =>
        opts ?= {}
        opts.onPlane ?= 1.0/@numPointsDep
        @current = new type @extents, opts

        for i in [1..@numPoints]
            @points[i] = @current.newPoint()
            @points[i][3] = @curTime + @delay(true)

        view.loadDynamics @current for view in @views

    goBackwards: () =>
        for point in @points
            @current.stepMat.applyToVector3Array point, 0, 3
        @direction = -1

    goForwards: () =>
        for point in @points
            @current.inverse.stepMat.applyToVector3Array point, 0, 3
        @direction = 1

    step: () =>
        if not @continuous and not @flow
            return if @startTime + @duration > @curTime
            @startTime = @curTime
        @goForwards() if @direction == -1
        for point, i in @points
            if i == 0  # Origin
                continue
            if point[3] + @duration <= @curTime
                # Reset point
                @current.stepMat.applyToVector3Array point, 0, 3
                @current.updatePoint point
                # Reset timer
                point[3] = @curTime + @delay()
        for view in @views
            view.pointsElt.set 'data', []
            view.pointsElt.set 'data', @points
        null

    unStep: () =>
        if not @continuous and not @flow
            return if @startTime + @duration > @curTime
            @startTime = @curTime
        @goBackwards() if @direction == 1
        inv = @current.inverse
        for point, i in @points
            if i == 0  # Origin
                continue
            if point[3] + @duration <= @curTime
                # Reset point
                inv.updatePoint point
                inv.stepMat.applyToVector3Array point, 0, 3
                # Reset timer
                point[3] = @curTime + @delay()
        for view in @views
            view.pointsElt.set 'data', []
            view.pointsElt.set 'data', @points
        null

    start: (interval=100) => setInterval @step, interval

    delay: (first) =>
        if not @continuous
            return if first then -@duration else 0
        scale = @numPoints / 1000
        pos = Math.random() * scale
        if first
            pos - 0.5 * scale
        else
            pos


######################################################################
# Dynamics base class

class Dynamics
    constructor: (@extents, opts) ->
        # Handle z-axis stuff if necessary
        @scaleZ = opts.scaleZ ? 0.0
        @onPlane = opts.onPlane ? 1/20
        if Math.abs(@scaleZ) < 1e-5
            @is3D = false
            @zAtTime = (start, t) -> 0
            @timeToLeaveZ = (start) -> Infinity
            @needsResetZ = (z) => false
        else if Math.abs(@scaleZ - 1) < 1e-5
            @is3D = true
            @scaleZ = 1.0
            @origLerpZ = linLerp 0.01, @extents.z
            @zAtTime = (start, t) -> start
            @timeToLeaveZ = (start) -> Infinity
            @needsResetZ = (z) => false
            # no @newLerpZ
        else if @scaleZ < 1.0
            @is3D = true
            @origLerpZ = expLerp 0.01,       @extents.z / @scaleZ
            @newLerpZ  = expLerp @extents.z, @extents.z / @scaleZ
            @zAtTime = (start, t) => start * Math.pow(@scaleZ, t)
            @timeToLeaveZ = (start) =>
                Math.log(0.01/Math.abs start) / Math.log(@scaleZ)
            @needsResetZ = (z) => Math.abs(z) < 0.01
        else if @scaleZ > 1.0
            @is3D = true
            @origLerpZ = expLerp 0.01 / @scaleZ, @extents.z
            @newLerpZ  = expLerp 0.01 / @scaleZ, 0.01
            @zAtTime = (start, t) => start * Math.pow(@scaleZ, t)
            @timeToLeaveZ = (start) =>
                Math.log(@extents.z/Math.abs start) / Math.log(@scaleZ)
            @needsResetZ = (z) => Math.abs(z) > @extents.z
        @invScaleZ = if @is3D then 1/@scaleZ else 0.0

    makeStepMat: (a, b, c, d) ->
        z = @scaleZ
        @stepMat22 = [[a, b], [c, d]]
        @stepMat = new THREE.Matrix4().set \
            a, b, 0, 0,
            c, d, 0, 0,
            0, 0, z, 0,
            0, 0, 0, 1

    timeToLeave: (point) =>
        x = @timeToLeaveZ(point[2])
        return x if isFinite(x) and x >= 0 and x <= 25
        x = @timeToLeaveXY(point[0], point[1])
        if x >= 0 and x <= 25 then x else Infinity

    newPoint: () =>
        if @is3D
            # A certain percentage of points go on the z=0 plane
            if Math.random() < @onPlane
                z = 0.0
            else
                z = randSign() * @origLerpZ Math.random()
        else
            z = 0
        xy = @origDistr()
        [xy[0], xy[1], z, 0]

    updatePoint: (point) =>
        if @needsResetXY point[0], point[1]
            # Point went out of bounds for xy-reasons.
            [point[0], point[1]] = @newDistr point
        return point unless @is3D and @scaleZ != 1.0
        return point if point[2] == 0.0 # Preserve z=0 plane
        # Point went out of bounds for z-reasons.  Don't change xy.
        point[2] = randSign() * @newLerpZ Math.random() if @needsResetZ point[2]
        point

    linesParams: () =>
        reference = @makeReference()
        channels: 2
        height:   reference.length
        width:    reference[0].length
        items:    reference[0][0].length
        live:     false
        data:     reference

    shaderParams: (params) ->
        params.uniforms ?= {}
        params.uniforms.scaleZ = { type: 'f', value: @scaleZ }
        params


######################################################################
# Complex eigenvalues

class Complex extends Dynamics
    constructor: (extents, opts) ->
        super extents, opts
        opts ?= {}
        @θ     = opts.θ     ? randSign() * linLerp(π/6, 5*π/6)(Math.random())
        @scale = opts.scale ? @randomScale()
        @logScale = Math.log @scale

        @makeStepMat Math.cos(@θ) * @scale, -Math.sin(@θ) * @scale,
                     Math.sin(@θ) * @scale,  Math.cos(@θ) * @scale

        @makeDistributions opts

    origDistr: () => @distr @origDist
    newDistr:  () => @distr @newDist

    distr: (distribution) =>
        r = distribution Math.random()
        θ = Math.random() * 2 * π
        [Math.cos(θ) * r, Math.sin(θ) * r]

    shaderParams: () =>
        super
            code: rotateShader,
            uniforms:
                deltaAngle: { type: 'f', value: @θ }
                scale:      { type: 'f', value: @scale }


class Circle extends Complex
    descr: () -> "Ovals"

    constructor: (extents, opts) ->
        super extents, opts
        @inverse = opts?.inverse ? new Circle extents,
            θ: -@θ
            scale: 1/@scale
            inverse: @
            scaleZ: @invScaleZ

    randomScale: () => 1

    makeDistributions: (opts) =>
        @newDist = @origDist = polyLerp 0.01, @extents.rad, 1/2

    makeReference: () =>
        ret = []
        for t in [0...2*π] by π/72
            row = []
            for s in [@extents.rad/10...@extents.rad] by @extents.rad/10
                row.push [s * Math.cos(t), s * Math.sin(t)]
            ret.push row
        ret.push ret[0] # Close the circle
        [ret]

    makePath: (start, path) =>
        ttl = @timeToLeave start
        if not isFinite ttl
            ttl = 2*π*(path.length+1) / (path.length * Math.abs @θ)
        totalAngle = ttl * @θ
        for i in [0...path.length]
            α = totalAngle * i/path.length
            c = Math.cos α
            s = Math.sin α
            path[i] = [c*start[0] - s*start[1], s*start[0] + c*start[1],
                       @zAtTime(start[2], ttl*i/path.length)]
        path

    needsResetXY: (x, y) -> false
    timeToLeaveXY: (x, y) -> Infinity


class Spiral extends Complex
    makeReference: () =>
        ret = []
        close = 0.1
        # How many iterations does it take to get from close to farthest?
        s = if @scale > 1 then @scale else 1/@scale
        iters = (Math.log(@extents.rad) - Math.log(close))/Math.log(s)
        # How many full rotations in that many iterations?
        rotations = Math.ceil(@θ * iters / 2*π)
        d = @direction
        # Have to put this in a matrix to avoid texture size limits
        for i in [0..rotations]
            row = []
            for t in [0..100]
                u = (i + t/100) * 2*π
                ss = close * Math.pow(s, u / @θ)
                items = []
                for j in [0...2*π] by π/4
                    items.push [ss * Math.cos(d*(u+j)), ss * Math.sin(d*(u+j))]
                row.push items
            ret.push row
        ret

    makePath: (start, path) =>
        ttl = @timeToLeave start
        if not isFinite ttl
            ttl = 2*π*(path.length+1) / (path.length * Math.abs @θ)
        totalAngle = ttl * @θ
        for i in [0...path.length]
            α = totalAngle * i/path.length
            c = Math.cos α
            s = Math.sin α
            t = ttl*i/path.length
            ss = Math.pow @scale, t
            path[i] = [ss*c*start[0] - ss*s*start[1],
                       ss*s*start[0] + ss*c*start[1],
                       @zAtTime(start[2], t)]
        path

class SpiralIn extends Spiral
    descr: () -> "Spiral in"

    constructor: (extents, opts) ->
        super extents, opts
        @direction = -1
        @inverse = opts?.inverse ? new SpiralOut extents,
            θ: -@θ
            scale: 1/@scale
            inverse: @
            dist: @distType
            scaleZ: @invScaleZ

    randomScale: () -> linLerp(0.3, 0.8)(Math.random())

    makeDistributions: (opts) =>
        @close  = 0.01
        @medium = @extents.rad
        @far    = @extents.rad / @scale

        @distType = opts.dist ? randElt ['cont', 'disc']

        switch @distType
            when 'cont'
                @origDist = expLerp @close, @far
                @newDist = expLerp @medium, @far
            when 'disc'
                distances = []
                distance = @far
                while distance > @close
                    distances.push distance
                    distance *= @scale
                @origDist = (t) -> distances[Math.floor(t * distances.length)]
                @newDist = (t) => @far

    needsResetXY: (x,y) => x*x+y*y < @close*@close

    timeToLeaveXY: (x, y) =>
        (Math.log(0.01) - .5*Math.log(x*x+y*y)) / @logScale


class SpiralOut extends Spiral
    descr: () -> "Spiral out"

    constructor: (extents, opts) ->
        super extents, opts
        @direction = 1
        @inverse = opts?.inverse ? new SpiralIn extents,
            θ: -@θ
            scale: 1/@scale
            inverse: @
            dist: @distType
            scaleZ: @invScaleZ

    randomScale: () => linLerp(1/0.8, 1/0.3)(Math.random())

    makeDistributions: (opts) =>
        @veryClose = 0.01 / @scale
        @close     = 0.01
        @medium    = @extents.rad

        @distType = opts.dist ? randElt ['cont', 'disc']

        switch @distType
            when 'cont'
                @origDist = expLerp @veryClose, @medium
                @newDist = expLerp @veryClose, @close
            when 'disc'
                distances = []
                distance = @veryClose
                while distance < @medium
                    distances.push distance
                    distance *= @scale
                @origDist = (t) -> distances[Math.floor(t * distances.length)]
                @newDist = (t) => @veryClose

    needsResetXY: (x, y) => x*x+y*y > @medium * @medium

    timeToLeaveXY: (x, y) =>
        (Math.log(@extents.rad) - .5*Math.log(x*x+y*y)) / @logScale


######################################################################
# Real eigenvalues, diagonalizable

class Diagonalizable extends Dynamics
    constructor: (extents, opts) ->
        super extents, opts
        opts ?= {}
        @swapped = false
        @makeScales opts
        λ1 = @λ1
        λ1 *= -1 if opts.negate1
        λ2 = @λ2
        λ2 *= -1 if opts.negate2
        if @swapped
            @makeStepMat λ2, 0, 0, λ1
        else
            @makeStepMat λ1, 0, 0, λ2

    swap: () =>
        [@λ2, @λ1] = [@λ1, @λ2]
        @extents =
            rad: @extents.rad
            x:   @extents.y
            y:   @extents.x
            z:   @extents.z
        @swapped = true

    shaderParams: () =>
        super
            code: diagShader,
            uniforms:
                scaleX: { type: 'f', value: if @swapped then @λ2 else @λ1 }
                scaleY: { type: 'f', value: if @swapped then @λ1 else @λ2 }

    makePath: (start, path) =>
        ttl = @timeToLeave start
        if not isFinite ttl
            ttl = 25 # Arbitrary
        if @swapped
            sx = @λ2
            sy = @λ1
        else
            sx = @λ1
            sy = @λ2
        for i in [0...path.length]
            t = ttl*i/path.length
            path[i] = [start[0] * Math.pow(sx, t),
                       start[1] * Math.pow(sy, t),
                       @zAtTime(start[2], t)]
        path


class Hyperbolas extends Diagonalizable
    descr: () -> "Hyperbolas"

    constructor: (extents, opts) ->
        super extents, opts
        [λ1, λ2] = if @swapped then [@λ2, @λ1] else [@λ1, @λ2]
        @inverse = opts?.inverse ? new Hyperbolas extents,
            λ1: 1/λ1
            λ2: 1/λ2
            inverse: @
            scaleZ: @invScaleZ

    makeScales: (opts) =>
        @λ1 = opts.λ1 ? linLerp(0.3, 0.8)(Math.random())
        @λ2 = opts.λ2 ? linLerp(1/0.8, 1/0.3)(Math.random())
        @swap() if @λ1 > @λ2
        # Implicit equations for paths are x^{log(λ2)}y^{-log(λ1)} = r
        @logScaleX = Math.log @λ1
        @logScaleY = Math.log @λ2
        # @close means (@close, @close) is the closest point to the origin
        @close = 0.05
        @closeR = Math.pow(@close, @logScaleY - @logScaleX)
        @farR = Math.pow(@extents.x, @logScaleY) * Math.pow(@extents.y, -@logScaleX)
        @lerpR = linLerp(@closeR, @farR)

    origDistr: () => @distr true
    newDistr: () => @distr false

    distr: (orig) =>
        # First choose r uniformly between @closeR and @farR
        r = @lerpR Math.random()
        if orig
            # x value on that hyperbola at y = @extents.y
            closeX = Math.pow(r * Math.pow(@extents.y, @logScaleX), 1/@logScaleY)
            # Choose x value exponentially along that hyperbola
            x = expLerp(closeX, @extents.x / @λ1)(Math.random())
        else
            # As above, but out of sight
            x = expLerp(@extents.x, @extents.x / @λ1)(Math.random())
        # Corresponding y
        y = Math.pow(1/r * Math.pow(x, @logScaleY), 1/@logScaleX)
        if @swapped
            [randSign() * y, randSign() * x]
        else
            [randSign() * x, randSign() * y]

    makeReference: () =>
        ret = []
        for t in [0...20]
            r = @lerpR t/20
            closeX = Math.pow(r * Math.pow(@extents.y, @logScaleX), 1/@logScaleY)
            lerp = expLerp closeX, @extents.x
            row = []
            for i in [0..100]
                x = lerp i/100
                y = Math.pow(1/r * Math.pow(x, @logScaleY), 1/@logScaleX)
                if @swapped
                    row.push [[y,  x], [ y, -x], [-y,  x], [-y, -x]]
                else
                    row.push [[x,  y], [-x,  y], [ x, -y], [-x, -y]]
            ret.push row
        ret

    needsResetXY: (x, y) => Math.abs(if @swapped then x else y) > @extents.y

    timeToLeaveXY: (x, y) =>
        y = x if @swapped
        (Math.log(@extents.y) - Math.log(Math.abs y)) / @logScaleY


class AttractRepel extends Diagonalizable
    makeScales: (opts) =>
        # Implicit equations for paths are x^{log(λ2)}y^{-log(λ1)} = r
        @logScaleX = Math.log @λ1
        @logScaleY = Math.log @λ2
        # Choose points on paths between the ones going through
        # (.95,.05) and (.05,.95)
        offset = 0.05
        # Interpolate r by choosing the path that goes through a random point on
        # the line y = 1-x
        @lerpR = (t) ->
            t = linLerp(offset, 1-offset)(t)
            Math.pow(t, @logScaleY) * Math.pow(1-t, -@logScaleX)
        # Assume this is >1
        a = @logScaleY/@logScaleX
        # Points expand in/out in "wave fronts" of the form x^a + y = s
        # Acting (x,y) by stepMat multiplies this equation by λ2
        # Last wave front is through (@extents.x, @extents.y)
        @sMin = 0.01
        @sMax = Math.pow(@extents.x, a) + @extents.y
        # The y-value of the point of intersection of the curves
        # x^a+y=s and x^lsy y^{-lsx} = r
        @yValAt = (r, s) -> s / (1 + Math.pow(r, 1/@logScaleX))
        # x as a function of y on the curve blah=r
        @xOfY = (y, r) -> Math.pow(r * Math.pow(y, @logScaleX), 1/@logScaleY)

    makeReference: () =>
        ret = []
        for i in [0...15]
            r = @lerpR i/15
            lerp = expLerp 0.01, @extents.y
            row = []
            for i in [0..100]
                y = lerp i/100
                x = @xOfY y, r
                row.push [[x,  y], [-x,  y], [ x, -y], [-x, -y]]
            ret.push row
        ret


class Attract extends AttractRepel
    descr: () -> "Attracting point"

    constructor: (extents, opts) ->
        super extents, opts
        @inverse = opts?.inverse ? new Repel extents,
            λ1: 1/@λ1
            λ2: 1/@λ2
            inverse: @
            scaleZ: @invScaleZ

    makeScales: (opts) =>
        @λ1 = opts.λ1 ? linLerp(0.3, 0.9)(Math.random())
        @λ2 = opts.λ2 ? linLerp(0.3, @λ1)(Math.random())
        if @λ1 < @λ2
            throw "Must pass smaller eigenvalue second"
        # λ1 >= λ2 implies logScaleY/logScaleX > 1
        super opts

    origDistr: () => @distr true
    newDistr: () => @distr false

    distr: (orig) =>
        # First choose r
        r = @lerpR Math.random()
        farY = @yValAt r, @sMax / @λ2
        if orig
            closeY = @yValAt r, @sMin
        else
            closeY = @yValAt r, @sMax
        y = expLerp(closeY, farY)(Math.random())
        x = @xOfY y, r
        [randSign() * x, randSign() * y]

    needsResetXY: (x, y) => Math.abs(y) < .01

    timeToLeaveXY: (x, y) =>
        (Math.log(0.01) - Math.log(Math.abs y)) / @logScaleY


class Repel extends AttractRepel
    descr: () -> "Repelling point"

    constructor: (extents, opts) ->
        super extents, opts
        @inverse = opts?.inverse ? new Attract extents,
            λ1: 1/@λ1
            λ2: 1/@λ2
            inverse: @
            scaleZ: @invScaleZ

    makeScales: (opts) =>
        @λ2 = opts.λ2 ? linLerp(1/0.9, 1/0.3)(Math.random())
        @λ1 = opts.λ1 ? linLerp(1/0.9, @λ2)(Math.random())
        if @λ1 > @λ2
            throw "Must pass smaller eigenvalue first"
        # λ1 <= λ2 implies logScaleY/logScaleX > 1
        super opts

    origDistr: () => @distr true
    newDistr: () => @distr false

    distr: (orig) =>
        # First choose r
        r = @lerpR Math.random()
        closeY = @yValAt r, @sMin / @λ2
        if orig
            farY = @yValAt r, @sMax
        else
            farY = @yValAt r, @sMin
        y = expLerp(closeY, farY)(Math.random())
        x = @xOfY y, r
        [randSign() * x, randSign() * y]

    needsResetXY: (x, y) => Math.abs(x) > @extents.x or Math.abs(y) > @extents.y

    timeToLeaveXY: (x, y) =>
        Math.min((Math.log(@extents.x) - Math.log(Math.abs x)) / @logScaleX,
                 (Math.log(@extents.y) - Math.log(Math.abs y)) / @logScaleY)


class AttractRepelLine extends Diagonalizable
    makeScales: (opts) =>
        @λ1 = 1
        @lerpX = linLerp -@extents.x, @extents.x

    origDistr: () => @distr @origLerpY
    newDistr: () => @distr @newLerpY

    distr: (distribution) =>
        x = @lerpX Math.random()
        y = distribution Math.random()
        [x, randSign() * y]

    makeReference: () =>
        item1 = []
        item2 = []
        for i in [0...20]
            x = @lerpX (i+.5)/20
            item1.push [x, -@extents.y]
            item2.push [x,  @extents.y]
        [[item1, item2]]


class AttractLine extends AttractRepelLine
    descr: () -> "Attracting line"

    constructor: (extents, opts) ->
        super extents, opts
        @inverse = opts?.inverse ? new RepelLine extents,
            λ1: 1/@λ1
            λ2: 1/@λ2
            inverse: @
            scaleZ: @invScaleZ

    makeScales: (opts) =>
        super opts
        @λ2 = opts.λ2 ? linLerp(0.3, 0.8)(Math.random())
        @origLerpY = expLerp 0.01, @extents.y / @λ2
        @newLerpY = expLerp @extents.y, @extents.y / @λ2

    needsResetXY: (x, y) => Math.abs(y) < 0.01

    timeToLeaveXY: (x, y) =>
        (Math.log(0.01) - Math.log(Math.abs y)) / @logScaleY


class RepelLine extends AttractRepelLine
    descr: () -> "Repelling line"

    constructor: (extents, opts) ->
        super extents, opts
        @inverse = opts?.inverse ? new AttractLine extents,
            λ1: 1/@λ1
            λ2: 1/@λ2
            inverse: @
            scaleZ: @invScaleZ

    makeScales: (opts) =>
        super opts
        @λ2 = opts.λ2 ? linLerp(1/0.8, 1/0.3)(Math.random())
        @origLerpY = expLerp 0.01 / @λ2, @extents.y
        @newLerpY = expLerp 0.01 / @λ2, 0.01

    needsResetXY: (x, y) => Math.abs(y) > @extents.y

    timeToLeaveXY: (x, y) =>
        (Math.log(@extents.y) - Math.log(Math.abs y)) / @logScaleY


######################################################################
# Real eigenvalues, not diagonalizable

class Shear extends Dynamics
    descr: () -> "Shear"

    constructor: (extents, opts) ->
        super extents, opts
        opts ?= {}
        @translate = opts.translate ? randSign() * linLerp(0.2, 2.0)(Math.random())
        @makeStepMat 1, @translate, 0, 1
        @lerpY = linLerp 0.01, @extents.y
        # For reference
        @lerpY2 = linLerp -@extents.y, @extents.y

        @inverse = opts?.inverse ? new Shear extents,
            translate: -@translate
            inverse: @
            scaleZ: @invScaleZ

    origDistr: () =>
        a = @translate
        y = @lerpY Math.random()
        # Put a few points on the x-axis
        if Math.random() < 0.005
            y = 0
            x = linLerp(-@extents.x, @extents.x)(Math.random())
        else
            if a < 0
                x = linLerp(-@extents.x, @extents.x - a*y)(Math.random())
            else
                x = linLerp(-@extents.x - a*y, @extents.x)(Math.random())
        s = randSign()
        [s*x, s*y]

    newDistr: (oldPoint) =>
        a = @translate
        # Don't change path
        y = Math.abs oldPoint[1]
        if a < 0
            x = linLerp(@extents.x, @extents.x - a*y)(Math.random())
        else
            x = linLerp(-@extents.x - a*y, -@extents.x)(Math.random())
        s = randSign()
        [s*x, s*y]

    shaderParams: () =>
        super
            code: shearShader,
            uniforms:
                scale:     { type: 'f', value: 1.0 }
                translate: { type: 'f', value: @translate }

    makeReference: () =>
        item1 = []
        item2 = []
        for i in [0...20]
            y = @lerpY2 (i+.5)/20
            item1.push [-@extents.x, y]
            item2.push [@extents.x, y]
        [[item1, item2]]

    needsResetXY: (x, y) => Math.abs(x) > @extents.x

    timeToLeaveXY: (x, y) =>
        e = if y > 0 then @extents.x else -@extents.x
        (e - x) / (@translate * y)

    makePath: (start, path) =>
        ttl = @timeToLeave start
        if not isFinite ttl
            ttl = 100 # Arbitrary but large
        for i in [0...path.length]
            t = ttl*i/path.length
            path[i] = [start[0] + t * @translate * start[1],
                       start[1],
                       @zAtTime(start[2], t)]
        path


class ScaleInOutShear extends Dynamics
    constructor: (extents, opts) ->
        super extents, opts
        opts ?= {}
        @translate = opts.translate ? randSign() * linLerp(0.2, 2.0)(Math.random())
        λ = @scale
        a = @translate
        @makeStepMat λ, λ*a, 0, λ
        # Paths have the form λ^t(r+ta, 1)
        @logScale = Math.log λ
        @xOfY = (r, y) -> y * (r + a*Math.log(y)/@logScale)
        # tan gives a nice looking plot
        @lerpR = (t) -> Math.tan((t - 0.5) * π)
        # for points
        @lerpR2 = (t) -> Math.tan((t/0.99 + 0.005 - 0.5) * π)

    origDistr: () => @distr @lerpY
    newDistr: () => @distr @lerpYNew

    distr: (distribution) =>
        # Choose a path
        r = @lerpR2 Math.random()
        y = distribution Math.random()
        x = @xOfY r, y
        s = randSign()
        [s*x, s*y]

    shaderParams: () =>
        super
            code: shearShader,
            uniforms:
                scale:     { type: 'f', value: @scale }
                translate: { type: 'f', value: @translate }

    makeReference: () =>
        ret = []
        numLines = 40
        for i in [1...numLines]
            r = @lerpR i/numLines
            row = []
            for j in [0...100]
                y = @lerpY j/100
                x = @xOfY r, y
                row.push [[x, y], [-x, -y]]
            ret.push row
        return ret

    makePath: (start, path) =>
        ttl = @timeToLeave start
        if not isFinite ttl
            ttl = 25 # Arbitrary
        λ = @scale
        a = @translate
        for i in [0...path.length]
            t = ttl*i/path.length
            ss = Math.pow(λ, t)
            path[i] = [ss * start[0] + ss * a * t * start[1],
                       ss * start[1],
                       @zAtTime(start[2], t)]
        path


class ScaleOutShear extends ScaleInOutShear
    descr: () -> "Scale-out shear"

    constructor: (@extents, opts) ->
        opts ?= {}
        @scale = opts.scale ? linLerp(1/0.7, 1/0.3)(Math.random())
        @lerpY = expLerp 0.01/@scale, @extents.y
        @lerpYNew = expLerp 0.01/@scale, 0.01
        super @extents, opts

        @inverse = opts?.inverse ? new ScaleInShear @extents,
            translate: -@translate
            scale: 1/@scale
            inverse: @
            scaleZ: @invScaleZ

    needsResetXY: (x, y) => Math.abs(y) > @extents.y

    timeToLeaveXY: (x, y) =>
        (Math.log(@extents.y) - Math.log(Math.abs y)) / @logScale


class ScaleInShear extends ScaleInOutShear
    descr: () -> "Scale-in shear"

    constructor: (@extents, opts) ->
        opts ?= {}
        @scale = opts.scale ? linLerp(0.3, 0.7)(Math.random())
        @lerpY = expLerp 0.01, @extents.y / @scale
        @lerpYNew = expLerp @extents.y, @extents.y / @scale
        super @extents, opts

        @inverse = opts?.inverse ? new ScaleOutShear @extents,
            translate: -@translate
            scale: 1/@scale
            inverse: @
            scaleZ: @invScaleZ

    needsResetXY: (x, y) => Math.abs(y) < .01

    timeToLeaveXY: (x, y) =>
        (Math.log(0.01) - Math.log(Math.abs y)) / @logScale


######################################################################
# Exports

window.dynamics = {}

window.dynamics.DynamicsView  = DynamicsView
window.dynamics.Controller    = Controller

window.dynamics.Circle        = Circle
window.dynamics.SpiralIn      = SpiralIn
window.dynamics.SpiralOut     = SpiralOut
window.dynamics.Hyperbolas    = Hyperbolas
window.dynamics.Attract       = Attract
window.dynamics.Repel         = Repel
window.dynamics.AttractLine   = AttractLine
window.dynamics.RepelLine     = RepelLine
window.dynamics.Shear         = Shear
window.dynamics.ScaleOutShear = ScaleOutShear
window.dynamics.ScaleInShear  = ScaleInShear



## -*- coding: utf-8 -*-

######################################################################
# * Test matrices

testMatrices =
    Shear:         [[2/3,   1/3 ], [-1/3,  4/3 ]]
    ScaleOutShear: [[5/3,   1/3 ], [-1/3,  7/3 ]]
    ScaleInShear:  [[1/3,   1/6 ], [-1/6,  2/3 ]]
    Circle:        [[1/3,  -1/3 ], [ 5/6,  2/3 ]]
    SpiralIn:      [[1/3,  -1/3 ], [ 5/6,  2/3 ]]
    SpiralOut:     [[2/3,  -2/3 ], [ 5/3,  4/3 ]]
    AttractLine:   [[5/6,   1/6 ], [ 1/3,  2/3 ]]
    RepelLine:     [[4/3,  -1/3 ], [-2/3,  5/3 ]]
    Attract:       [[7/18, -1/18], [-1/9,  4/9 ]]
    Repel:         [[8/3,   1/3 ], [ 2/3,  7/3 ]]
    Hyperbolas:    [[8/9,  -5/9 ], [-10/9, 13/9]]

for row in testMatrices.Circle
    row[0] *= Math.sqrt 2
    row[1] *= Math.sqrt 2

######################################################################
# * Compute standard form of the 2x2 block matrix

almostZero = (x) -> Math.abs(x) < 1e-5

normalize = (b) ->
    n = Math.sqrt(b[0]*b[0] + b[1]*b[1])
    [b[0]/n, b[1]/n]

mv3v2 = (v1, v2, b) -> [
        v1[0]*b[0] + v2[0]*b[1],
        v1[1]*b[0] + v2[1]*b[1],
        v1[2]*b[0] + v2[2]*b[1],
    ]

matrixInfo = (matrix) ->
    [[a, b], [c, d]] = matrix
    trace = a + d
    determinant = a*d - b*c
    discriminant = trace*trace - 4*determinant

    # These are the parameters that are computed below
    basis1 = []
    basis2 = []
    type = null
    opts = {}
    axisColors = [new Color("green") .arr(1),
                  new Color("violet").arr(1),
                  new Color("brown") .arr(1)]
    eigenStrs = []

    if almostZero determinant
        throw "Can't handle non-invertible matrix"

    # One real eigenvalue
    if almostZero discriminant
        λ = trace / 2
        if λ < 0
            throw "Can't handle negative real eigenvalues"
        # Diagonalizable iff it's a scalar matrix
        if almostZero(b) and almostZero(c)
            basis1 = [1, 0]
            basis2 = [0, 1]
            axisColors[1] = axisColors[0]
            eigenStrs.push "The whole plane is the <span class=\"espace-1\">" +
                           "#{λ.toFixed 2}-eigenspace.</span>"
            type = if λ > 1 then dynamics.Repel else dynamics.Attract
            opts =
                λ1: λ
                λ2: λ
        # Shear: put it in the form [λ, λ*a, 0, λ]
        else
            if almostZero b
                basis1 = normalize [λ-d, c]
            else
                basis1 = normalize [b, λ-a]
            basis2 = [basis1[1], -basis1[0]]  # Anything linearly independent
            axisColors[1] = [0.5, 0.5, 0.5, 0.3]
            eigenStrs.push "This is the <span class=\"espace-1\">" +
                           "#{λ.toFixed 2}-eigenspace.</span>"
            # (matrix - λ) * basis2 = (λ * translate) basis1
            v = [(a-λ)*basis2[0] + b*basis2[1], c*basis2[0] + (d-λ)*basis2[1]]
            if almostZero basis1[0]
                opts.translate = v[1] / (λ*basis1[1])
            else
                opts.translate = v[0] / (λ*basis1[0])
            if almostZero (λ-1)
                type = dynamics.Shear
            else
                if λ > 1
                    type = dynamics.ScaleOutShear
                else
                    type = dynamics.ScaleInShear
                opts.scale = λ

    # Rotation-scaling matrix
    else if discriminant < 0
        Reλ = trace / 2
        Imλ = Math.sqrt(-discriminant) / 2
        basis1 = [b/Imλ, (Reλ-a)/Imλ]
        basis2 = [0, 1]
        axisColors[0] = [0.5, 0.5, 0.5, 0.3]
        axisColors[1] = [0.5, 0.5, 0.5, 0.3]
        str  = 'This matrix has complex eigenvalues '
        str += katex.renderToString "\\lambda = #{Reλ.toFixed 2}\\pm #{Imλ.toFixed 2}i."
        eigenStrs.push str
        opts =
            θ:     Math.atan2 -Imλ, Reλ
            scale: Math.sqrt determinant
            dist:  'cont'

        if almostZero(opts.scale-1)
            type = dynamics.Circle
        else
            if opts.scale > 1
                type = dynamics.SpiralOut
            else
                type = dynamics.SpiralIn

    # Diagonalizable real matrix
    else if discriminant > 0
        δ = Math.sqrt discriminant
        λ1 = (trace - δ) / 2
        λ2 = (trace + δ) / 2
        negate1 = false
        negate2 = false
        if λ1 < 0
            λ1 *= -1
            negate1 = true
        if λ2 < 0
            λ2 *= -1
            negate2 = true
        if λ1 >= λ2
            [λ2, λ1] = [λ1, λ2]
            [negate2, negate1] = [negate1, negate2]
        opts =
            λ1: λ1
            λ2: λ2
            negate1: negate1
            negate2: negate2
        if almostZero b
            if almostZero c
                # Already diagonal
                if almostZero (a-λ1)
                    basis1 = [1, 0]
                    basis2 = [0, 1]
                else
                    basis2 = [1, 0]
                    basis1 = [0, 1]
            else
                basis1 = normalize [λ1-d, c]
                basis2 = normalize [λ2-d, c]
        else
            basis1 = normalize [b, λ1-a]
            basis2 = normalize [b, λ2-a]
        swap = () ->
            [opts.negate2, opts.negate1] = [opts.negate1, opts.negate2]
            [opts.λ2, opts.λ1] = [opts.λ1, opts.λ2]
            [basis2, basis1] = [basis1, basis2]
        if almostZero(λ1-1)
            type = dynamics.RepelLine
        else if almostZero(λ2-1)
            type = dynamics.AttractLine
            swap()
        else if λ1 < 1 and λ2 < 1
            type = dynamics.Attract
            swap()
        else if λ1 < 1 and λ2 > 1
            type = dynamics.Hyperbolas
        else if λ1 > 1 and λ2 > 1
            type = dynamics.Repel
        λ1p = opts.λ1 * (if opts.negate1 then -1 else 1)
        λ2p = opts.λ2 * (if opts.negate2 then -1 else 1)
        eigenStrs.push "This is the <span class=\"espace-1\">" +
                       "#{λ1p.toFixed 2}-eigenspace.</span>"
        eigenStrs.push "This is the <span class=\"espace-2\">" +
                       "#{λ2p.toFixed 2}-eigenspace.</span>"

    basis1:     basis1
    basis2:     basis2
    type:       type
    typeOpts:   opts
    axisColors: axisColors
    eigenStrs:  eigenStrs


######################################################################
# * Demo

dynamicsDemo = (controller, opts) ->
    axes       = opts.axes ? false
    grid       = opts.grid ? false
    dynView    = opts.dynView
    params     = opts.params
    eigenStr   = opts.eigenStr
    matName    = opts.matName    ? 'A'
    vecName    = opts.vecName    ? 'x'
    size       = opts.size       ? 2
    eigenz     = opts.eigenz     ? 1
    suffix     = opts.suffix     ? ''
    element    = opts.element    ? document.getElementById "mathbox"
    captionElt = opts.captionElt ? document.getElementById "caption"
    vecColor   = opts.vecColor   ? new Color("red")
    numPoints  = opts.numPoints  ? 10
    dragHook   = opts.dragHook   ? () ->

    vectorIn  = opts.vectorIn?.slice() ? [.5, 0, 0]
    vectorsOut = ([0,0,0] for [0..numPoints])
    [vectorsOut[0][0], vectorsOut[0][1], vectorsOut[0][2]]=vectorIn

    demo = window.demo = new (if size == 3 then Demo else Demo2D) {
        mathbox:
            element: element
            size: aspect: 1
        vertical: 1.05
    }, () ->
        view = @view
            viewRange: [[-1, 1], [-1, 1], [-1, 1]]
            axes:      axes
            grid:      grid
        clipCube = @clipCube view,
            draw:   size == 3
            hilite: false

        dynView.updateView @mathbox, clipCube.clipped

        @dynView = dynView
        @controller = controller

        ##################################################
        # Caption
        te = dynView.matrixOrigCoords.elements
        if size == 2
            displayMat = [[te[0], te[1]], [te[4], te[5]]]
        else if size == 3
            displayMat = [[te[0], te[1], te[2]],
                          [te[4], te[5], te[6]],
                          [te[8], te[9], te[10]]]

        str  = "<p><span id=\"mat-here#{suffix}\"></span>" +
               "<span id=\"mult-here#{suffix}\"></span></p>"
        str += eigenStr
        captionElt.innerHTML = str

        matElt = document.getElementById "mat-here#{suffix}"
        multElt = document.getElementById "mult-here#{suffix}"
        str = "#{matName} = " + @texMatrix displayMat
        katex.render str, matElt

        updateCaption = () =>
            vin  = vectorsOut[0].slice  0, size
            vout = vectorsOut[1].slice 0, size
            str = '\\qquad ' + matName +
                  @texVector((x*10 for x in vin), color: vecColor) +
                  " = " +
                  @texVector((x*10 for x in vout), color: vecColor.darken(-.1))
            katex.render str, multElt

  ##################################################
        # Test vector
        viewT = dynView.view

        labeled = @labeledPoints view,
            points:        vectorsOut
            colors:        [vecColor, vecColor.darken(-.07),  vecColor.darken(-.14), vecColor.darken(-.22)].concat (vecColor.darken(-.3) for [4..numPoints]) #[vecColor, vecColor.darken(-.1),  vecColor.darken(-.2), vecColor.darken(-.3), vecColor.darken(-.3)]
            labels:        [vecName, matName + vecName, matName+"²"+vecName, matName+"³"+vecName].concat ("" for [4..numPoints])
            live:          true
            zeroPoints:    false
            zeroThreshold: 0.3
            vectorOpts:    zIndex: 4
            labelOpts:     zIndex: 5
            zeroOpts:      zIndex: 5

        if size == 2
            snap = () ->
        else if size == 3
            # Snap to base plane
            subspace = @subspace vectors: [dynView.v1, dynView.v2]
            snapped = new THREE.Vector3()
            diff = new THREE.Vector3()
            snap = (vec) ->
                subspace.project vec, snapped
                diff.copy(vec).sub snapped
                if diff.lengthSq() <= 0.01
                    vec.copy snapped

        drag = @draggable view,
            points: [vectorsOut[0]]
            onDrag: snap
            postDrag: () ->
                computeOut()
                computePath()
                dragHook vectorIn

        minorIterator = (i) ->
            [vectorsOut[i][0], vectorsOut[i][1], vectorsOut[i][2]] = vectorsOut[i-1]
            dynView.matrixOrigCoords.applyToVector3Array vectorsOut[i]

        computeOut = () ->
            return unless params["Test vector"]
            minorIterator(i) for i in [1..numPoints]
            updateCaption()

        @setVec = (vec) ->
            [vectorsOut[0][0], vectorsOut[0][1], vectorsOut[0][2]] = vec
            computeOut()
            computePath()

        @toggleVector = (val) =>
            drag.enabled = params["Test vector"] or params["Show path"]
            if val
                labeled.show()
                computeOut()
                multElt.classList.remove "hidden"
            else
                labeled.hide()
                multElt.classList.add "hidden"
        @toggleVector params["Test vector"]


        ##################################################
        # Test path
        path = ([0,0,0] for [0..100])
        computePath = () =>
            return unless params["Show path"]
            vec = vectorsOut[0].slice()
            dynView.coordMatInv.applyToVector3Array vec
            controller.current.makePath vec, path
        viewT.array
            channels: 3
            width:    path.length
            live:     true
            data:     path
        pathElt = viewT.line
            color:    vecColor.darken(-0.3).arr()
            width:    5
            opacity:  0.3
            zBias:    0
            zIndex:   4

        @togglePath = (val) =>
            computePath() if val
            pathElt.set 'visible', val
            drag.enabled = params["Test vector"] or params["Show path"]
        @togglePath params["Show path"]


