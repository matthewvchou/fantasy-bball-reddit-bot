import sqlite3

from src.ingest.franchises import loadFranchises
from src.ingest.ingest import NBA_TEAM_ID_RANGES, ingestSeason
from tests.fakesource import FixtureSource

OKLAHOMA_CITY_THUNDER_ID = 1610612760


def testSonicsAndThunderAreOneFranchiseWithBothNames(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)

    franchiseCount = dbConnection.execute(
        "SELECT COUNT(*) FROM franchise WHERE teamId = ?", (OKLAHOMA_CITY_THUNDER_ID,),
    ).fetchone()[0]
    names = dbConnection.execute(
        "SELECT city, name, startYear, endYear FROM franchiseName WHERE teamId = ? AND name IN ('SuperSonics', 'Thunder')",
        (OKLAHOMA_CITY_THUNDER_ID,),
    ).fetchall()
    assert franchiseCount == 1
    # The source also lists a whole-franchise row (1967-2026) under the Thunder name; it is kept as given.
    assert sorted(set(names)) == [
        ("Oklahoma City", "Thunder", 1967, 2026),
        ("Oklahoma City", "Thunder", 2008, 2026),
        ("Seattle", "SuperSonics", 1967, 2007),
    ]


def testBobcatsAndHornetsAreOneFranchise(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)

    teamIds = dbConnection.execute(
        "SELECT DISTINCT teamId FROM franchiseName WHERE (city, name) IN (('Charlotte', 'Bobcats'), ('Charlotte', 'Hornets'))",
    ).fetchall()
    assert teamIds == [(1610612766,)]


def testStoresRowsThatMatchInEveryStoredFieldOnce(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)

    # The source lists Charlotte's Hornets (1988-2026) twice: a whole-franchise row and a name row,
    # which differ only in years played and games, columns this database does not keep.
    hornetsRows = dbConnection.execute(
        "SELECT COUNT(*) FROM franchiseName WHERE teamId = ? AND name = 'Hornets' AND startYear = 1988",
        (1610612766,),
    ).fetchone()[0]
    assert hornetsRows == 1


def testADefunctTeamIsItsOwnFranchiseWithNoSuccessor(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)

    # The Chicago Stags folded in 1949.
    franchise = dbConnection.execute("SELECT * FROM franchise WHERE teamId = ?", (1610610025,)).fetchone()
    names = dbConnection.execute("SELECT city, name, startYear, endYear FROM franchiseName WHERE teamId = ?", (1610610025,)).fetchall()
    assert franchise == (1610610025, 1)
    assert names == [("Chicago", "Stags", 1946, 1949)]
    # No successor column exists to point at another Franchise.
    columns = [column[1] for column in dbConnection.execute("PRAGMA table_info(franchise)")]
    assert columns == ["teamId", "isDefunct"]


def testACurrentTeamIsNotMarkedDefunct(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)

    isDefunct = dbConnection.execute("SELECT isDefunct FROM franchise WHERE teamId = ?", (OKLAHOMA_CITY_THUNDER_ID,)).fetchone()[0]
    assert isDefunct == 0


def testEveryTeamOnAStoredGameResolvesToAFranchise(dbConnection: sqlite3.Connection) -> None:
    for season in ["1970-71", "1990-91", "2023-24", "2024-25"]:
        ingestSeason(FixtureSource(), dbConnection, season)
    loadFranchises(FixtureSource(), dbConnection)

    gameCount = dbConnection.execute("SELECT COUNT(*) FROM game").fetchone()[0]
    unresolved = dbConnection.execute(
        "SELECT COUNT(*) FROM game WHERE homeTeamId NOT IN (SELECT teamId FROM franchise) "
        "OR awayTeamId NOT IN (SELECT teamId FROM franchise)",
    ).fetchone()[0]
    assert gameCount > 0
    assert unresolved == 0


def testFranchiseIdsMatchTheNbaTeamIdsTheIngestAccepts(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)

    storedIds = {row[0] for row in dbConnection.execute("SELECT teamId FROM franchise")}
    acceptedIds = {teamId for idRange in NBA_TEAM_ID_RANGES for teamId in idRange}
    assert storedIds == acceptedIds


def testALoadIsLoggedAndARerunLeavesTheRowsUnchanged(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)
    loadFranchises(FixtureSource(), dbConnection)

    counts = dbConnection.execute("SELECT (SELECT COUNT(*) FROM franchise), (SELECT COUNT(*) FROM franchiseName)").fetchone()
    log = dbConnection.execute("SELECT kind, unitKey, status, rowCount FROM ingestLog").fetchall()
    assert counts == (45, 88)
    assert log == [("franchiseHistory", "all", "done", 133)]


def testRefreshReplacesTheStoredFranchises(dbConnection: sqlite3.Connection) -> None:
    loadFranchises(FixtureSource(), dbConnection)
    dbConnection.execute("UPDATE franchiseName SET name = 'Wrong' WHERE name = 'Thunder'")
    dbConnection.commit()

    loadFranchises(FixtureSource(), dbConnection, shouldRefresh=True)

    wrongCount = dbConnection.execute("SELECT COUNT(*) FROM franchiseName WHERE name = 'Wrong'").fetchone()[0]
    thunderCount = dbConnection.execute("SELECT COUNT(*) FROM franchiseName WHERE name = 'Thunder'").fetchone()[0]
    assert (wrongCount, thunderCount) == (0, 2)
