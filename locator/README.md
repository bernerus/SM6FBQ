
`maidenhead` provides a simple, yet effective location hashing algorithm.
Maidenhead allows arvitrary precision depending on the length of the locator code.

This code provides 8 levels of increasing accuracy

  Level |  Precision       | Latitude distance |  Example code
--------|------------------------------------------------------
  1     |  10x20°          | 1113 km           |  IO
  2     |  1x2°            | 111 km            |  IO96
  3     |  2.5 x 5'        | 4.6 km            |  IO96xc
  4     |  15 x 30"        | 463 m             |  IO96xc74
  5*    |  0.625 x 1.25"   | 19.3 m            |  IO96xc74tt
  6*    |  0.0625 x 0.125" | 1.9 m             |  IO96xc74tt12

* The levels 5 and 6 are not internationally agreed upon. 
  Here they are a recursive extension of the levels 3 and 4
 

## Examples

All examples assume first doing

```python
import locator as mh
```

### lat lon to Maidenhead locator

```python
mh.to_maiden(lat, lon, level)
```

returns a char (len = lvl*2)

### Maidenhead locator to lat lon

```python
mh.to_location('AB01cd')
```

takes Maidenhead location string and returns top-left lat, lon of Maidenhead grid square.

## Command Line

The command line interface takes either decimal degrees for "latitude longitude" or the Maidenhead locator string:

```sh
maidenhead 65.0 -148.0
```

> BP65aa

```sh
maidenhead BP65aa12
```

> 65.0083 -147.9917

The "python -m" CLI is also available:

```sh
python -m maidenhead 65.0 -148.0
```


## Alternatives

We also have
[Maidenhead conversion for Julia](https://github.com/space-physics/maidenhead-julia).

Open Location Codes a.k.a Plus Codes are in
[Python code by Google](https://github.com/google/open-location-code/tree/master/python).
