from pandas import DataFrame

from scripts.extract_flybase_fbbt_phenotypes import next_upheno_id


def populate_upheno_ids(df: DataFrame, upheno_prefix: str) -> DataFrame:
    """
    Given a DataFrame with anatomical_entity column, create a new column upheno_id
    :param df: DataFrame
    :param upheno_prefix: str
    :return: DataFrame
    """
    df['upheno_id'] = df['anatomical_entity'].apply(lambda x: upheno_prefix + str(next_upheno_id(df)))
    return df