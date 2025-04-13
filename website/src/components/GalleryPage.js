import React, { useEffect, useState, useCallback } from "react";
import { Card, List, Select, Typography } from "antd";
import { useLocation, useHistory } from "react-router-dom";

const { Option } = Select;
const { Paragraph, Title } = Typography;

const GalleryPage = (props) => {
  const location = useLocation();
  const history = useHistory();

  // Function to get tags from the URL query string.
  const getTagsFromURL = useCallback(() => {
    const searchParams = new URLSearchParams(location.search);
    const tags = searchParams.get("tags");
    return tags ? tags.split(",") : [];
  }, [location.search]);

  // Initialize selectedTags state based on URL parameters.
  const [selectedTags, setSelectedTags] = useState(getTagsFromURL());

  useEffect(() => {
    // Update state if the URL search parameters change.
    const tagsFromURL = getTagsFromURL();
    setSelectedTags(tagsFromURL);
  }, [getTagsFromURL]);

  const TagsView = ({ tags }) => (
    <div className="tags-container">
      {tags?.map((tag, index) => (

        <span className="tag" key={index} onClick={(evt) => {
          if (!selectedTags.includes(tag)) {
            handleTagChange([...selectedTags, tag])
          }
          evt.preventDefault();
          evt.stopPropagation();
          return false;
        }} >
          {tag}
        </span>
      ))}
    </div>
  );

  const allTags = [...new Set(props.items.flatMap((item) => item.tags))];

  const handleTagChange = (tags) => {
    setSelectedTags(tags);
    const searchParams = new URLSearchParams();
    if (tags.length > 0) {
      searchParams.set("tags", tags.join(","));
    }
    history.push(`${location.pathname}?${searchParams.toString()}`);
  };

  const filteredData =
    selectedTags.length > 0
      ? props.items.filter((item) =>
        selectedTags.some((tag) => item.tags.includes(tag))
      )
      : props.items;

  const defaultImageIfNoImage = props.allowDefaultImage ?? true;
  const imageFunc = (item) => {
    const image =
      <img
        alt={item.title}
        src={
          item.image
            ? item.image.includes("http")
              ? item.image
              : `/autogen/0.2/img/gallery/${item.image}`
            : `/autogen/0.2/img/gallery/default.png`
        }
        style={{
          height: 150,
          width: "fit-content",
          margin: "auto",
          padding: 2,
        }}
      />
      ;

    const imageToUse = item.image ? image : defaultImageIfNoImage ? image : null;
    return imageToUse;
  }

  const badges = (item) => {
    if (!item.source) {
      return null;
    }
    const colab_href = `https://colab.research.google.com/github/microsoft/autogen/blob/main/${item.source}`;
    const github_href = `https://github.com/microsoft/autogen/blob/0.2/${item.source}`;
    return (<span>
      <a style={{marginRight: '5px'}}href={colab_href} target="_parent"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a>
      <a href={github_href} target="_parent"><img alt="Static Badge" src="https://img.shields.io/badge/Open%20on%20GitHub-grey?logo=github"/></a>
      </span>
    );
  }

  const target = props.target ?? "_blank";
  return (
    <div>
      <Select
        mode="multiple"
        placeholder="Filter by tags"
        style={{ width: "100%", marginBottom: 16 }}
        value={selectedTags}
        onChange={handleTagChange}
        aria-label="Filter by tags"
      >
        {allTags.map((tag) => (
          <Option key={tag} value={tag}>
            {tag}
          </Option>
        ))}
      </Select>

      <List
        grid={{
          gutter: 16,
          xs: 1,
          sm: 2,
          md: 2,
          lg: 3,
          xl: 4,
          xxl: 4,
        }}
        dataSource={filteredData}
        renderItem={(item) => (
          <List.Item>
            <a
              href={item.link}
              target={target}
              rel="noopener noreferrer"
              style={{ display: "block" }}
            >
              <Card
                hoverable
                bordered
                style={{ height: 370, paddingTop: imageFunc(item) ? 15 : 0 }}
                cover={imageFunc(item)}
              >
                <Title level={5} ellipsis={{ rows: 4 }}>
                  {item.title}
                </Title>
                {badges(item)}

                <Paragraph
                  ellipsis={{ rows: imageFunc(item) ? 3 : 6 }}
                  style={{
                    fontWeight: "normal",
                    color: "#727272",
                  }}
                >
                  {item.description ? item.description : item.title}
                </Paragraph>
                <TagsView tags={item.tags} />
              </Card>
            </a>
          </List.Item>
        )}
      />
    </div>
  );
};

export default GalleryPage;
