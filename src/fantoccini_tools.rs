use fantoccini::{elements::Element, error::CmdError, Client, Locator};

pub async fn find_in(
    client: &Client,
    parent_loc: &Option<Locator<'_>>,
    target_loc: &Locator<'_>,
) -> Result<Element, CmdError> {
    if let Some(parent_loc) = parent_loc {
        client.find(*parent_loc).await?.find(*target_loc).await
    } else {
        client.find(*target_loc).await
    }
}

pub async fn find_all_in(
    client: &Client,
    parent_loc: &Option<Locator<'_>>,
    target_loc: &Locator<'_>,
) -> Result<Vec<Element>, CmdError> {
    if let Some(parent_loc) = parent_loc {
        client.find(*parent_loc).await?.find_all(*target_loc).await
    } else {
        client.find_all(*target_loc).await
    }
}
