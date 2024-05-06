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
import GavelIcon from '@mui/icons-material/Gavel';
import { styled } from '@mui/material/styles';
import { green, pink } from '@mui/material/colors';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';

const data = [
  { icon: <HandshakeTwoToneIcon sx={{ color: green[500] }} />, label: 'IPA discount form 9-9 - eur 15k' },
  { icon: <GavelIcon  sx={{ color: green[500] }}  />, label: '2x1 brewery birthday - eur 250k' },
  { icon: <HandshakeTwoToneIcon  sx={{ color: green[500] }}  />, label: 'Summer day 1 - CHF 180k' },
  { icon: <HandshakeTwoToneIcon  sx={{ color: pink[500] }}  />, label: 'Worldcup promo 1.5M' },
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

export default function CostList() {
  const [open, setOpen] = React.useState(false);
  console.log(`[Marketing] Rendering.`);

  return (
    <Box sx={{ display: 'flex' }}>
      <FireNav component="nav" disablePadding>
        <Box
          sx={{
            //bgcolor: open ? 'rgba(71, 98, 130, 0.2)' : null,
            //pb: open ? 2 : 0,
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
            <ListItemIcon sx={{ my: 0, opacity: 1,  class: "menuicon"}}>
              <AttachMoneyIcon/>
            </ListItemIcon>
            <ListItemText
              primary="Economy of similar cases" 
              primaryTypographyProps={{
                fontSize: 15,
                fontWeight: 'medium',
                lineHeight: '20px',
                mb: '2px',
              }}
              secondary="Cost of similar cases in the past"
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
          {open &&
            data.map((item) => (
              <ListItemButton
                key={item.label}
                sx={{ py: 0, minHeight: 32, color: 'rgba(255,255,255,.8)' }}
              >
                <ListItemIcon sx={{ color: 'inherit' }}>
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{ fontSize: 14, fontWeight: 'medium' }}
                />
              </ListItemButton>
            ))}
        </Box>
      </FireNav>
    </Box>
  );
}