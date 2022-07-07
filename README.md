# Nanome - High Quality Surfaces

A Nanome Plugin to run [MSMS](https://www.scripps.edu/sanner/html/msms_home.html) that computes molecular surfaces and load them in Nanome.
(Molecular Surface by Michel Sanner)

This plugin also computes Ambient Occlusion (AO) to darken buried parts of the molecular surfaces using https://github.com/nezix/AOEmbree

<img width="750" alt="High Quality Surfaces Tab 1" src="https://user-images.githubusercontent.com/18257337/173958022-13855bc0-471c-4c9e-80fd-22a3f088da59.png">
<img width="750" alt="High Quality Surfaces Tab 2" src="https://user-images.githubusercontent.com/18257337/173958028-ba54c77a-246b-474d-97ba-181d54aae584.png">

## Dependencies

[Docker](https://docs.docker.com/get-docker/)

## Usage

To run the plugin in a Docker container:

```sh
$ cd docker
$ ./build.sh
$ ./deploy.sh -a <plugin_server_address> [optional args]
```

## Development

To run the High Quality Surfaces plugin with autoreload:

```sh
$ python3 -m pip install -r requirements.txt
$ python3 run.py -r -a <plugin_server_address> [optional args]
```

## Citation

[Sanner, M. F., Olson A.J. & Spehner, J.-C. (1996). Reduced Surface: An Efficient Way to Compute Molecular Surfaces. Biopolymers 38:305-320.](https://onlinelibrary.wiley.com/doi/abs/10.1002/(SICI)1097-0282(199603)38:3%3C305::AID-BIP4%3E3.0.CO;2-Y)

## License

MIT
