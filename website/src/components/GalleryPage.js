import React, { useEffect, useState, useCallback } from "react";
import galleryData from "../data/gallery.json";
import { Card, List, Select } from "antd";
import { useLocation, useHistory } from "react-router-dom";

const { Option } = Select;

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
          md: 3,
          lg: 3,
          xl: 4,
          xxl: 4,
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
                  />
                }
              >
                <div>
                  <span
                    style={{
                      fontSize: "1.2rem",
                      fontWeight: "bold",
                      color: "black",
                    }}
                  >
                    {item.title}
                  </span>
                </div>
                <div
                  style={{
                    // fontSize: "0.8rem",
                    fontWeight: "normal",
                    color: "grey",
                  }}
                >
                  {item.description ? item.description : item.title}
                </div>
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
