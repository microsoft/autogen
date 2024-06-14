"use client";

import * as React from 'react';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import KeyboardArrowDown from '@mui/icons-material/KeyboardArrowDown';
import Public from '@mui/icons-material/Public';
import HandshakeTwoToneIcon from '@mui/icons-material/HandshakeTwoTone';
import WorkspacePremiumTwoToneIcon from '@mui/icons-material/WorkspacePremiumTwoTone';
import { styled } from '@mui/material/styles';
import FolderIcon from '@mui/icons-material/Folder';
import ExpandLess from '@mui/icons-material/ExpandLess';
import ExpandMore from '@mui/icons-material/ExpandMore';
import Collapse from '@mui/material/Collapse';
import FilePresentIcon from '@mui/icons-material/FilePresent';

const data = [
  { icon: <HandshakeTwoToneIcon />, label: 'Internal guidance for marketing campaigns' },
  { icon: <WorkspacePremiumTwoToneIcon />, label: 'Belgium law on marketing of alcohol' },
  { icon: <Public />, label: 'something else' },
];

const FireNav = styled(List)<{ component?: React.ElementType }>({
  '& .MuiListItemButton-root': {
    paddingLeft: 24,
    paddingRight: 24,
  },
  '& .MuiListItemIcon-root': {
    minWidth: 0,
    marginRight: 16,
  },
  '& .MuiSvgIcon-root': {
    fontSize: 20,
  },
});

export default function RelevantDocumentList() {
  const [open, setOpen] = React.useState(false);
  console.log(`[Marketing] Rendering.`);

  const [courtCasesOpen, setCourtCasesOpen] = React.useState(true);
  const courtCasesOpenHandleClick = () => {
    setCourtCasesOpen(!courtCasesOpen);
  };

  const [lawOpen, setLawOpen] = React.useState(true);
  const LawOpenHandleClick = () => {
    setLawOpen(!lawOpen);
  };


  return (
    <Box sx={{ display: 'flex' }}>
      <FireNav component="nav" disablePadding>
        <Box
          sx={{
            bgcolor: open ? 'rgba(71, 98, 130, 0.2)' : null,
            pb: open ? 2 : 0,
          }}
        >
          <ListItemButton
            alignItems="flex-start"
            onClick={() => setOpen(!open)}
            sx={{
              px: 3,
              pt: 2.5,
              pb: open ? 0 : 2.5,
              '&:hover, &:focus': { '& #arrowdownicon': { opacity: open ? 1 : 0 } },
            }}
          >
            <ListItemIcon sx={{ my: 0, opacity: 1, class: "menuicon" }}>
              <FilePresentIcon />
            </ListItemIcon>
            <ListItemText
              primary="Relevant files"
              primaryTypographyProps={{
                fontSize: 15,
                fontWeight: 'medium',
                lineHeight: '20px',
                mb: '2px',
              }}
              secondary="Files that might be relevant to your case."
              secondaryTypographyProps={{
                noWrap: true,
                fontSize: 12,
                lineHeight: '16px',
                color: open ? 'rgba(0,0,0,0)' : 'rgba(255,255,255,0.5)',
              }}
              sx={{ my: 0 }}
            />
            <KeyboardArrowDown
              id="arrowdownicon"
              sx={{
                mr: -1,
                opacity: 0,
                transform: open ? 'rotate(-180deg)' : 'rotate(0)',
                transition: '0.2s',
              }}
            />
          </ListItemButton>
          {open && (
            <Box>
              <List
                sx={{ bgcolor: 'background.paper', textAlign: 'left' }}
                component="nav"
                aria-labelledby="nested-list-subheader"
              >
                {/* Court cases */}
                <List>
                  <ListItemButton onClick={courtCasesOpenHandleClick}>
                    <ListItemIcon>
                      <FolderIcon />
                    </ListItemIcon>
                    <ListItemText primary="Internal docs" />
                    {courtCasesOpen ? <ExpandLess /> : <ExpandMore />}
                  </ListItemButton>
                  <Collapse in={courtCasesOpen} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding>
                      <ListItemButton>
                        <ListItemIcon sx={{ pl: 4 }}>
                          <img src="/static/icons/docs.png" height={20} width={20} />
                        </ListItemIcon>
                        <ListItemText primary="Marketing campaings general guidelines" />
                      </ListItemButton>
                      <ListItemButton>
                        <ListItemIcon sx={{ pl: 4 }}>
                          <img src="/static/icons/pdf.png" height={20} width={20} />
                        </ListItemIcon>
                        <ListItemText primary="Marketing regulations in Belgium" />
                      </ListItemButton>
                    </List>
                  </Collapse>
                </List>
                {/* Laws */}
                <List>
                  <ListItemButton onClick={LawOpenHandleClick}>
                    <ListItemIcon>
                      <FolderIcon />
                    </ListItemIcon>
                    <ListItemText primary="Public " />
                    {lawOpen ? <ExpandLess /> : <ExpandMore />}
                  </ListItemButton>
                  <Collapse in={lawOpen} timeout="auto" unmountOnExit>
                    <List component="div" disablePadding>
                      <ListItemButton>
                        <ListItemIcon sx={{ pl: 4 }}>
                          <img src="/static/icons/edge.png" height={20} width={20} />
                        </ListItemIcon>
                        <ListItemText primary="Worldwide discount" />
                      </ListItemButton>
                      <ListItemButton>
                        <ListItemIcon sx={{ pl: 4 }}>
                          <img src="/static/icons/edge.png" height={20} width={20} />
                        </ListItemIcon>
                        <ListItemText primary="Color week - T-Shitrs 2022" />
                      </ListItemButton>
                    </List>
                  </Collapse>
                </List>
              </List>
            </Box>
          )}
        </Box>
      </FireNav>
    </Box>
  );
}