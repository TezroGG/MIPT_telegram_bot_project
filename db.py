import sqlalchemy as sa
import sqlalchemy.orm as orm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SqlAlchemyBase = orm.declarative_base()

__factory: async_sessionmaker[AsyncSession] | None = None
__engine = None


class ArtistGenre(SqlAlchemyBase):
    __tablename__ = "artist_genres"
    artist_id = sa.Column(sa.String, primary_key=True)
    genres = sa.Column(sa.JSON, nullable=True)


class TrackCache(SqlAlchemyBase):
    __tablename__ = "track_cache"
    track_id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String, nullable=False)
    album = sa.Column(sa.String, nullable=True)
    popularity = sa.Column(sa.Integer, nullable=True)
    duration_ms = sa.Column(sa.Integer, nullable=True)
    is_local = sa.Column(sa.Boolean, default=False)
    artist_id = sa.Column(sa.String, nullable=True)
    genres = sa.Column(sa.JSON, nullable=True)


async def db_init(db_file):
    global __factory, __engine

    if __factory is not None:
        return

    if len(db_file) == 0:
        raise Exception("Необходимо указать файл базы данных.")

    conn_str = f"sqlite+aiosqlite:///{db_file}"
    __engine = create_async_engine(conn_str, echo=False, future=True)
    __factory = async_sessionmaker(bind=__engine, expire_on_commit=False, class_=AsyncSession)

    async with __engine.begin() as conn:
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


def create_session():
    global __factory
    if __factory is None:
        raise Exception("База данных не инициализирована.")
    return __factory()


async def get_artist_genres_cached(session, artist_id):
    row = await session.scalar(select(ArtistGenre).where(ArtistGenre.artist_id == artist_id))
    return row.genres if row else None


async def set_artist_genres_cached(session, artist_id, genres):
    row = await session.scalar(select(ArtistGenre).where(ArtistGenre.artist_id == artist_id))
    if row:
        row.genres = genres
    else:
        session.add(ArtistGenre(artist_id=artist_id, genres=genres))


async def cache_track(session, track_dict, artist_genres):
    track_id = track_dict.get("id")
    if not track_id:
        return

    row = await session.scalar(select(TrackCache).where(TrackCache.track_id == track_id))

    album_name = track_dict["album"]["name"]
    artist_id = track_dict["artists"][0]["id"]

    data = dict(
        track_id=track_id,
        name=track_dict.get("name"),
        album=album_name,
        popularity=track_dict.get("popularity"),
        duration_ms=track_dict.get("duration_ms"),
        is_local=bool(track_dict.get("is_local",   False)),
        artist_id=artist_id,
        genres=artist_genres,
    )

    if row:
        for key, val in data.items():
            setattr(row, key, val)
    else:
        session.add(TrackCache(**data))
