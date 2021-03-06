import os.path

from geopandas import GeoDataFrame
from geopandas.testing import (
    geom_equals, geom_almost_equals, assert_geoseries_equal)  # flake8: noqa

HERE = os.path.abspath(os.path.dirname(__file__))
PACKAGE_DIR = os.path.dirname(os.path.dirname(HERE))


try:
    import psycopg2
    from psycopg2 import OperationalError
except ImportError:
    class OperationalError(Exception):
        pass

try:
    import unittest.mock as mock
except ImportError:
    import mock


def validate_boro_df(df, case_sensitive=False):
    """ Tests a GeoDataFrame that has been read in from the nybb dataset."""
    assert isinstance(df, GeoDataFrame)
    # Make sure all the columns are there and the geometries
    # were properly loaded as MultiPolygons
    assert len(df) == 5
    columns = ('BoroCode', 'BoroName', 'Shape_Leng', 'Shape_Area')
    if case_sensitive:
        for col in columns:
            assert col in df.columns
    else:
        for col in columns:
            assert col.lower() in (dfcol.lower() for dfcol in df.columns)
    assert all(df.geometry.type == 'MultiPolygon')


def connect(dbname):
    try:
        con = psycopg2.connect(dbname=dbname)
    except (NameError, OperationalError):
        return None

    return con


def create_db(df):
    """
    Create a nybb table in the test_geopandas PostGIS database.
    Returns a boolean indicating whether the database table was successfully
    created

    """
    # Try to create the database, skip the db tests if something goes
    # wrong
    # If you'd like these tests to run, create a database called
    # 'test_geopandas' and enable postgis in it:
    # > createdb test_geopandas
    # > psql -c "CREATE EXTENSION postgis" -d test_geopandas
    con = connect('test_geopandas')
    if con is None:
        return False

    try:
        cursor = con.cursor()
        cursor.execute("DROP TABLE IF EXISTS nybb;")

        sql = """CREATE TABLE nybb (
            geom        geometry,
            borocode    integer,
            boroname    varchar(40),
            shape_leng  float,
            shape_area  float
        );"""
        cursor.execute(sql)

        for i, row in df.iterrows():
            sql = """INSERT INTO nybb VALUES (
                ST_GeometryFromText(%s), %s, %s, %s, %s
            );"""
            cursor.execute(sql, (row['geometry'].wkt,
                                 row['BoroCode'],
                                 row['BoroName'],
                                 row['Shape_Leng'],
                                 row['Shape_Area']))
    finally:
        cursor.close()
        con.commit()
        con.close()

    return True


