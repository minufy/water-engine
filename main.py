from water_engine import Engine, build_demo_scene


if __name__ == "__main__":
    engine = Engine()
    engine.load_scene(build_demo_scene(engine))
    engine.run()
