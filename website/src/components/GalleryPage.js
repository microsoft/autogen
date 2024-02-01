import React, { useEffect, useState, useCallback } from "react";
import galleryData from "../data/gallery.json";
import { Card, List, Select, Typography } from "antd";
import { useLocation, useHistory } from "react-router-dom";

const { Option } = Select;
const { Paragraph, Title } = Typography;

const GalleryPage = () => {
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
      {tags.map((tag, index) => (
        <span className="tag" key={index}>
          {tag}
        </span>
      ))}
    </div>
  );

  const allTags = [...new Set(galleryData.flatMap((item) => item.tags))];

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
      ? galleryData.filter((item) =>
          selectedTags.some((tag) => item.tags.includes(tag))
        )
      : galleryData;

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
          lg: 2,
          xl: 3,
          xxl: 3,
        }}
        dataSource={filteredData}
        renderItem={(item) => (
          <List.Item>
            <a
              href={item.link}
              target="_blank"
              rel="noopener noreferrer"
              style={{ display: "block" }}
            >
              <Card
                hoverable
                bordered
                style={{ height: 370, paddingTop: 15 }}
                cover={
                  <img
                    alt={item.title}
                    src={
                      item.image
                        ? item.image.includes("http")
                          ? item.image
                          : `/autogen/img/gallery/${item.image}`
                        : `/autogen/img/gallery/default.png`
                    }
                    style={{
                      height: 150,
                      width: "fit-content",
                      margin: "auto",
                      padding: 2,
                    }}
                  />
                }
              >
                <Title level={5} ellipsis={{ rows: 2 }}>
                  {item.title}
                </Title>
                <Paragraph
                  ellipsis={{ rows: 3 }}
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
