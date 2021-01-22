from flask import Flask, render_template
import locator.src.maidenhead as mh

import math

app = Flask(__name__, template_folder="./templates")
GoogleMaps(app, key='AIzaSyDyHlT4j3tWgPK1FkTFZfsSskSIkYTS5Sw')


def circle(size, user_location):
    c = {  # draw circle on map (user_location as center)
        'stroke_color': '#0000FF',
        'stroke_opacity': .5,
        'stroke_weight': 1,
        # line(stroke) style
        'fill_color': '#FFFFFF',
        'fill_opacity': 0,
        # fill style
        'center': {  # set circle to user_location
            'lat': user_location[0],
            'lng': user_location[1]
        },
        'radius': size
    }
    return c


@app.route("/")
def mapview():
    az = 73

    n, s, w, e, lon, lat = mh.to_rect("JO67BQ68SL59")

    user_location = (lon, lat)

    rect = {
        "stroke_color": '#0000FF',
        "stroke_opacity": .7,
        "stroke_weight": 1,
        "fill_color": None,
        "fill_opacity": 0,
        "bounds": {
            "north": n,
            "west": w,
            "south": s,
            "east": e,
        },
    }

    antrad = 0.01

    azrad = 2 * math.pi / 360 * (90 - az)

    front_lat = user_location[0] + antrad * math.sin(azrad)
    front_lon = user_location[1] + antrad * math.cos(azrad)

    ant = {
        "id": "dj9bv",
        "icon": "//maps.google.com/mapfiles/arrow.png",
        "stroke_color": '#0000FF',
        "stroke_opacity": .7,
        "stroke_weight": 2,
        "fill_color": None,
        "fill_opacity": 0,
        "rotation": 78,
        "scale": 12,
        "lat": user_location[0],
        "lng": user_location[1],
    }

    # creating a map in the view
    mymap = Map(
        identifier="view-side",
        lat=57.702129,
        lng=-122.1419,
        markers=[(37.4419, -122.1419)]
    )
    sndmap = Map(
        identifier="sndmap",
        lat=user_location[0],
        lng=user_location[1],
        markers=[ant, ],
        # circles=[circle(size, user_location) for size in [1000, 2000, 3000, 5000, 10000, 100000, 1000000]],
        rectangles=[rect, ],
    )
    return render_template('example.html', sndmap=sndmap)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8877, debug=True)
