import Modal from "antd/es/modal/Modal";
import * as React from "react";

const ExpandView = ({ children, className = "" }: any) => {
  const [isOpen, setIsOpen] = React.useState(false);
  return (
    <div className={`border rounded mb-6  border-secondary ${className}`}>
      <div
        role="button"
        onClick={() => {
          setIsOpen(true);
        }}
        className="text-xs mb-2 break-words"
      >
        {children}
      </div>
      {isOpen && (
        <Modal
          width={800}
          open={isOpen}
          onCancel={() => setIsOpen(false)}
          footer={null}
        >
          {children}
        </Modal>
      )}
    </div>
  );
};
export default ExpandView;
