# Frenetic Manual

For the impatient: https://github.com/frenetic-lang/manual/blob/master/programmers_guide/frenetic_programmers_guide.pdf

## Building From Source

The official documentation toolchain is LaTeX.  
TeXLive 2015 (or later) package has everything you need to build.

- TeXLive for Windows installation instructions are at http://www.tug.org/texlive/acquire-netinstall.html
- TeXLive for Mac, or MacTeX, installation instructions are at https://tug.org/mactex/

Then use whatever IDE you're comfortable with (TeXshop, etc.) to run programmers_guide/frenetic_programmers_guide.tex.
Alternatively, from the command line you can run:

```
$ cd programmers_guide
$ make
```

## Testing Code From the Guide

All code in the Frenetic Programmers Guide can be tested with the automatic test harness. 
To run:

```
$ cd programmers_guide/code/test
$ sudo python test_suite.py
```

The test takes about 15 minutes to run on a MacBook under Frenetic User VM.  